"""Automatic JSON unpacking to [`Polars`](https://pola.rs) `DataFrame` or `LazyFrame`.

The use case is as follows:

* Provide a schema written in plain text describing some JSON content, to be converted
  into a `Polars` `Struct` (see [samples](/samples) in this repo for examples).
* Read said JSON content, as plain text using `scan_csv()` for instance, or directly as
  JSON via `scan_ndjson()` and automagically unpack the nested content by processing the
  schema (_spoiler: the plain text way is better suited for our needs in the current_
  `Polars` _implementation_).

A few extra points:

* The schema should be dominant and we should rename fields as they are being unpacked
  to avoid identical names for different columns (which is forbidden by `Polars` for
  obvious reasons).
* _But why not simply using the inferred schema?_ Because at times we need to provide
  fields that might _not_ be in the JSON file to fit a certain data structure, or ignore
  part of the JSON data when unpacking to avoid wasting resources. Oh, and to rename
  fields too.

The requirements are illustrated below (JSON input, plain text schema, `Polars` output):

```json
{
    "column": "content",
    "nested": [
        {
            "attr": 0,
            "attr2": 2
        },
        {
            "attr": 1,
            "attr2": 3
        }
    ],
    "omitted_in_schema": "ignored"
}
```
```text
column: String
nested: List(
    Struct(
        attr: UInt8
        attr2=renamed: UInt8
    )
)
missing_from_source: Float32
```
```text
┌─────────┬──────┬─────────┬─────────────────────┐
│ column  ┆ attr ┆ renamed ┆ missing_from_source │
│ ---     ┆ ---  ┆ ---     ┆ ---                 │
│ str     ┆ ui8  ┆ ui8     ┆ f32                 │
╞═════════╪══════╪═════════╪═════════════════════╡
│ content ┆ 0    ┆ 2       ┆ null                │
│ content ┆ 1    ┆ 3       ┆ null                │
└─────────┴──────┴─────────┴─────────────────────┘
```

The current working state of this little DIY can be checked (in `Docker`) via:

```shell
$ make env
> python unpack.py tests/samples/complex.schema tests/samples/complex.ndjson
```

Note that a call to the same script _without_ providing a schema returns a
representation of the latter as _inferred_ by `Polars` (works as an example of the
syntax used to describe things in plain text):

```shell
$ make env
> python unpack.py tests/samples/complex.ndjson
```

A thorough(-ish) battery of tests can be performed (in `Docker`) via:

```shell
$ make test
```

Although testing various functionalities, these tests are pretty independent. But the
`test_real_life()` functions working on a common example
([schema](/tests/samples/complex.schema) & [data](/tests/samples/complex.ndjson)) are
there to check if this is only fantasy. Running is convincing!

Feel free to cherry-pick and extend the functionalities to your own use cases.
"""

import pathlib
import re
import sys

import polars as pl

POLARS_DATATYPES: dict[str, pl.DataType] = {
    "array": pl.List,
    "list": pl.List,
    "struct": pl.Struct,
    "float32": pl.Float32,
    "float64": pl.Float64,
    "int8": pl.Int8,
    "int16": pl.Int16,
    "int32": pl.Int32,
    "int64": pl.Int64,
    "uint8": pl.UInt8,
    "uint16": pl.UInt16,
    "uint32": pl.UInt32,
    "uint64": pl.UInt64,
    "utf8": pl.String,
    # shorthands
    "float": pl.Float64,
    "real": pl.Float64,
    "int": pl.Int64,
    "integer": pl.Int64,
    "string": pl.String,
}


def infer_schema(path_data: str) -> str:
    """Lazily scan newline-delimited JSON data and print the `Polars`-inferred schema.

    We expect the following example JSON:

    ```json
    { "attribute": "test", "nested": { "foo": 1.23, "bar": -8, "vector": [ 0, 1, 2 ] } }
    ```

    to translate into the given `Polars` schema:

    ```text
    attribute: String
    nested: Struct(
        foo: Float32
        bar: Int16
        vector: List(UInt8)
    )
    ```

    Although this merely started as a test for the output of the schema parser defined
    somewhere below in this very script, it became quite useful to get a head start when
    writing a schema by hand.

    Parameters
    ----------
    path_data : str
        Path to a JSON file for `Polars` to infer its own schema (_e.g._, `Struct`
        object).

    Returns
    -------
    : str
        Pretty-printed `Polars` JSON schema.

    """

    # quick work
    def _pprint(field: str, dtype: pl.DataType, indent: str = "") -> str:
        """Recursively loop over the inferred schema and pretty print its structure.

        Parameters
        ----------
        field : str
            Name of the current field, including `:` separator.
        dtype : polars.DataType
            Datatype of the current field; nested or not.
        indent : str
            String used to indent (a number of spaces?); defaults to empty string
            (`""`).

        Returns
        -------
        : str
            Pretty-printed field name and datatype of the current field.

        """
        schema = ""

        # nested datatype: Struct
        if hasattr(dtype, "fields"):
            schema += f"{indent}{field}{dtype.__class__.__name__}(\n"
            for f, d in dtype.to_schema().items():
                schema += _pprint(f"{f}: ", d, f"{indent}    ")
            schema += f"{indent})\n"

        # nested datatypes: Array, List
        elif hasattr(dtype, "inner"):
            schema += f"{indent}{field}{dtype.__class__.__name__}(\n"
            schema += _pprint("", dtype.inner, f"{indent}    ")
            schema += f"{indent})\n"

        # non-nested datatypes
        else:
            schema += f"{indent}{field}{dtype}\n"

        return schema

    # generate the pretty-printed schema
    schema = ""
    for field, dtype in pl.scan_ndjson(path_data).schema.items():
        schema += _pprint(f"{field}: ", dtype)

    return schema.strip()


def parse_schema(path_schema: str) -> pl.Struct:
    """Parse a plain text JSON schema into a `Polars` `Struct`.

    Parameters
    ----------
    path_schema : str
        Path to the plain text file describing the JSON schema.

    Returns
    -------
    : polars.Struct
        JSON schema translated into `Polars` datatypes.

    """
    with pathlib.Path(path_schema).open() as f:
        sp = SchemaParser(f.read())
        sp.to_struct()

        return sp


def unpack_ndjson(path_schema: str, path_data: str) -> pl.LazyFrame:
    """Lazily scan and unpack newline-delimited JSON file given a `Polars` schema.

    Parameters
    ----------
    path_schema : str
        Path to the plain text schema describing the JSON content.
    path_data : str
        Path to the JSON file (or multiple files via glob patterns).

    Returns
    -------
    : polars.LazyFrame
        Unpacked JSON content, lazy style.

    Notes
    -----
    * Fields described in the schema but absent from the JSON source will be added as
      `null` values.
    * Fields present in the JSON source but absent from the schema will be dropped.

    """
    s = parse_schema(path_schema)

    # read as json and unpack the object
    df = pl.scan_ndjson(path_data).json.unpack(s.struct)

    # add missing columns
    df = df.with_columns(
        [
            pl.lit(None).cast(d).alias(p)
            for p, d in zip(s.json_paths.keys(), s.dtypes, strict=True)
            if p not in df.columns
        ],
    )

    # rename fields (otherwise renamed to their full json paths)
    df = df.rename(s.json_paths)

    # final selection (drop extra/unwanted columns)
    return df.select(s.columns)


def unpack_text(
    path_schema: str,
    path_data: str,
    separator: str = "|",
    **kwargs,
) -> pl.LazyFrame:
    r"""Lazily scan and unpack JSON data read as plain text, given a `Polars` schema.

    Parameters
    ----------
    path_schema : str
        Path to the plain text schema describing the JSON content.
    path_data : str
        Path to the JSON file (or multiple files via glob patterns).
    separator : str
        Separator to use when parsing the JSON file as a CSV; defaults to `|` but `#` or
        `$` could be good candidates too (as are UTF-8 characters?). Note this separator
        should \*NOT\* be present in the file at all (`,` or `:` are thus out of
        question given the JSON context).

    Returns
    -------
    : polars.LazyFrame
        Unpacked JSON content, lazy style.

    Notes
    -----
    This is mostly a test, to verify the output would be identical, as this unpacking
    use case could be applied on a CSV column containing some JSON content for instance.
    The preferred way for native JSON content remains the `unpack_ndjson()` function
    defined in this same script.

    In the current `Polars` implementation this function is however better suited for
    the use case: the provided schema is always dominant, regardless of the content of
    the JSON file. We do not need to add or remove missing or supplementary columns,
    everything is taken care of by the `json_extract()` method.

    """
    s = parse_schema(path_schema)

    # read as plain text
    # unpack object and rename fields (otherwise renamed to their full json paths)
    # no other transformations are necessary as the schema is already dominant here
    return (
        pl.scan_csv(
            path_data,
            has_header=False,
            new_columns=["raw"],
            separator=separator,
            **kwargs,
        )
        .select(pl.col("raw").str.json_decode(s.struct))
        .unnest("raw")
        .json.unpack(s.struct)
        .rename(s.json_paths)
    )


class SchemaParser:
    """Parse a plain text JSON schema into a `Polars` `Struct`."""

    def __init__(self, source: str = "", separator: str = ".") -> None:
        """Instantiate the object.

        Parameters
        ----------
        source : str
            JSON schema described in plain text, using `Polars` datatypes; defaults to
            an empty string (`""`).
        separator : str
            JSON path separator to use when building the full JSON path; defaults to a
            dot (`.`).

        Attributes
        ----------
        columns : list[str]
            Expected list of columns in the final `Polars` `DataFrame` or `LazyFrame`.
        dtypes : list[polars.DataType]
            Expected list of datatypes in the final `Polars` `DataFrame` or `LazyFrame`.
        json_paths : dit[str, str]
            Dictionary of JSON path -> column name pairs.
        separator : str
            JSON path separator to use when building the full JSON path.
        source : str
            JSON schema described in plain text, using `Polars` datatypes.
        struct : polars.Struct
            Plain text schema parsed as a `Polars` `Struct`.

        """
        self.source = source
        self.separator = separator

        self.columns: list[str] = []
        self.dtypes: list[pl.DataType] = []
        self.json_paths: dict[str, str] = {}
        self.struct: pl.Struct | None = None

    def format_error(self, unparsed: str) -> str:
        """Format the message printed in the exception when an issue occurs.

        ```text
        Tripped on line 2

             1 │ headers: Struct(
             2 │     timestamp: Foo
             ? │                ^^^
        ```

        Parameters
        ----------
        unparsed : str
            Unexpected string that raised the exception.

        Returns
        -------
        : str
            Clean and helpful error message, helpfully.

        Notes
        -----
        * In most cases this method will look for the first occurrence of the string
          that raised the exception; and it might not be the _actual_ line that did so.
        * This method is absolutely useless and could be removed.

        """
        # start/end of the issue
        issue_start = self.source.index(unparsed)
        issue_end = (
            issue_start + m.start()
            if (m := re.search(r"[()\[\]{}<>\n]", self.source[issue_start:]))
            is not None
            else len(self.source)
        )

        # start/end of the line
        line_start = (
            issue_start - self.source[:issue_start][::-1].index("\n") + 1
            if issue_start and "\n" in self.source[:issue_start]
            else 1
        )
        line_end = (
            issue_end + self.source[issue_end:].index("\n")
            if "\n" in self.source[issue_end:]
            else len(self.source)
        )

        # line number at which the issue happens
        line_number = self.source[:issue_start].count("\n") + 1

        # captain obvious
        msg = f"Tripped on line {line_number}\n\n"
        for i, line in enumerate(self.source[:line_end].split("\n")):
            msg += f"   {i + 1:-3d} │ {line}\n"
        msg += "     ? │ "
        msg += " " * (issue_start - line_start + 1)
        msg += "^" * (issue_end - issue_start)
        msg += "\n"

        return msg

    def parse_renamed_attr_dtype(
        self,
        struct: pl.Struct,
        name: str,
        renamed_to: str,
        dtype: str,
    ) -> pl.Struct:
        """Parse and register an attribute, its new name, and its associated datatype.

        Parameters
        ----------
        struct : polars.Struct
            Current state of the `Polars` `Struct`.
        name : str
            Current attribute name.
        renamed_to : str
            New name for the attribute.
        dtype : str
            Expected `Polars` datatype for this attribute.

        Returns
        -------
        : polars.Struct
            Updated `Polars` `Struct` including the latest parsed addition.

        Raises
        ------
        : DuplicateColumnError
            When a column is encountered more than once in the schema.
        : UnknownDataTypeError
            When an unknown/unsupported datatype is encountered.

        """
        # sanity check
        if dtype.lower() not in POLARS_DATATYPES:
            raise UnknownDataTypeError(self.format_error(dtype))

        dtype = dtype.lower()
        field = pl.Field(name, POLARS_DATATYPES[dtype])

        # add to the lists
        if dtype not in ("array", "list", "struct"):
            if renamed_to not in self.columns:
                self.columns.append(renamed_to)
                self.dtypes.append(POLARS_DATATYPES[dtype])

                # json path and associated column name
                path = (
                    self.separator.join(self.record["path"])
                    .replace("[]", "")
                    .replace(self.separator * 2, self.separator)
                    .rstrip(self.separator)
                )
                self.json_paths[
                    f"{path}{self.separator}{name}".lstrip(self.separator)
                ] = renamed_to
            else:
                raise DuplicateColumnError(self.format_error(renamed_to))

        # renaming part of the json path is not supported (nor needed)
        else:
            raise PathRenamingError(renamed_to)

        # keep track of the nested object encountered, or if non-nested add it to the
        # the current nested object, or the root struct
        if self.record["parents"]:
            self.record["structs"][-1].append(field)
        else:
            struct.append(field)

        return struct

    def parse_attr_dtype(self, struct: pl.Struct, name: str, dtype: str) -> pl.Struct:
        """Parse and register an attribute and its associated datatype.

        Parameters
        ----------
        struct : polars.Struct
            Current state of the `Polars` `Struct`.
        name : str
            Attribute name.
        dtype : str
            Expected `Polars` datatype for this attribute.

        Returns
        -------
        : polars.Struct
            Updated `Polars` `Struct` including the latest parsed addition.

        Raises
        ------
        : DuplicateColumnError
            When a column is encountered more than once in the schema.
        : UnknownDataTypeError
            When an unknown/unsupported datatype is encountered.

        """
        # sanity check
        if dtype.lower() not in POLARS_DATATYPES:
            raise UnknownDataTypeError(self.format_error(dtype))

        dtype = dtype.lower()
        field = pl.Field(name, POLARS_DATATYPES[dtype])

        # add to the lists
        if dtype not in ("array", "list", "struct"):
            if name not in self.columns:
                self.columns.append(name)
                self.dtypes.append(POLARS_DATATYPES[dtype])

                # json path and associated column name
                path = (
                    self.separator.join(self.record["path"])
                    .replace("[]", "")
                    .replace(self.separator * 2, self.separator)
                    .rstrip(self.separator)
                )
                self.json_paths[
                    f"{path}{self.separator}{name}".lstrip(self.separator)
                ] = name
            else:
                raise DuplicateColumnError(self.format_error(name))

        # add the parent to the current path
        else:
            self.record["path"].append(name)

        # keep track of the nested object encountered, or if non-nested add it to the
        # the current nested object, or the root struct
        if dtype in ("list", "struct"):
            self.record["parents"].append((name, dtype))
        elif self.record["parents"]:
            self.record["structs"][-1].append(field)
        else:
            struct.append(field)

        return struct

    def parse_lone_dtype(self, struct: pl.Struct, dtype: str) -> pl.Struct:
        """Parse and register a standalone datatype (found within a list for instance).

        Parameters
        ----------
        struct : polars.Struct
            Current state of the `Polars` `Struct`.
        dtype : str
            Expected `Polars` datatype.

        Returns
        -------
        : polars.Struct
            Updated `Polars` `Struct` including the latest parsed addition.

        Raises
        ------
        : UnknownDataTypeError
            When an unknown/unsupported datatype is encountered.

        """
        # sanity check
        if dtype.lower() not in POLARS_DATATYPES:
            raise UnknownDataTypeError(self.format_error(dtype))

        dtype = dtype.lower()

        # add to the path
        if dtype in ("list", "struct"):
            self.record["path"].append("[]")

        # keep track of the nested object encountered, or if non-nested add it to the
        # the current nested object, or the root struct
        if dtype in ("list", "struct"):
            self.record["parents"].append(("", dtype))
        elif self.record["parents"]:
            self.record["lists"].append(POLARS_DATATYPES[dtype])
        else:
            struct.append(pl.Field("", POLARS_DATATYPES[dtype]))

        return struct

    def parse_opening_delimiter(self) -> None:
        """Parse and register the opening of a nested structure."""
        # create a new list to register new fields
        if self.record["parents"][-1][1] == "struct":
            self.record["structs"].append([])

    def parse_closing_delimiter(self, struct: pl.Struct) -> pl.Struct:
        """Parse and register the closing of a nested structure.

        Parameters
        ----------
        struct : polars.Struct
            Current state of the `Polars` `Struct`.

        Returns
        -------
        : polars.Struct
            Updated `Polars` `Struct` including the latest parsed addition.

        """
        name, dtype = self.record["parents"].pop()

        # remove a parent from the current path
        if self.record["path"]:
            self.record["path"].pop()

        # list
        if dtype == "list":
            f = self.record["lists"].pop()
            d = f.dtype if hasattr(f, "dtype") else f

            # list within struct or list within list
            field = pl.Field(name, pl.List(d)) if name else pl.List(d)

        # struct
        else:
            field = pl.Field(name, pl.Struct(self.record["structs"].pop()))

        # add the attribute to the current nested object, or the root struct
        if self.record["parents"]:
            if self.record["parents"][-1][1] == "list":
                self.record["lists"].append(field)
            else:
                self.record["structs"][-1].append(field)
        else:
            struct.append(field)

        return struct

    def to_struct(self) -> pl.Struct:
        r"""Parse the plain text schema into a `Polars` `Struct`.

        We expect something as follows:

        ```text
        attribute: String
        nested: Struct(
            foo: Float32
            bar=bax: Int16
            vector: List[UInt8]
        )
        ```

        to translate into a `Polars` native `Struct` object:

        ```python
        polars.Struct([
            polars.Field("attribute", polars.String),
            polars.Struct([
                polars.Field("foo", polars.Float32),
                polars.Field("bar", polars.Int16),
                polars.Field("vector", polars.List(polars.UInt8))
            ])
        ])
        ```

        The following patterns (recognised via regular expressions) are supported:

        * `([A-Za-z0-9_]+)\s*=\s*([A-Za-z0-9_]+)\s*:\s*([A-Za-z0-9]+)` for an attribute
          name, an equal sign (`=`), a new name for the attribute, a column (`:`) and a
          datatype.
        * `([A-Za-z0-9_]+)\s*:\s*([A-Za-z0-9]+)` for an attribute name, a column (`:`)
          and a datatype; for instance `attribute: String` in the example above.
        * `([A-Za-z0-9]+)` for a lone datatype; for instance the inner content of the
          `List()` in the example above. Keep in mind this datatype could be a complex
          structure as much as a canonical datatype.
        * `[(\[{<]` and its `[)\]}>]` counterpart for opening and closing of nested
          datatypes. Any of these characters can be used to open or close nested
          structures; mixing also allowed, for the better or the worse.

        Note attribute names and datatypes must not contain spaces and only include
        alphanumerical or underscore (`_`) characters.

        Indentation and trailing commas are ignored. The source is parsed until the end
        of the file is reached or a `SchemaParsingError` exception is raised.

        Returns
        -------
        : polars.Struct
            Plain text schema parsed as a `Polars` `Struct`.

        Raises
        ------
        : SchemaParsingError
            When unexpected content is encountered and cannot be parsed.

        """
        s = self.source
        struct: list[pl.Datatype] = []

        # bookkeeping
        self.record: dict = {"lists": [], "parents": [], "path": [], "structs": []}

        # continue until everything is parsed
        while s:
            if (
                m := re.match(
                    r"([A-Za-z0-9_]+)\s*=\s*([A-Za-z0-9_]+)\s*:\s*([A-Za-z0-9]+)",
                    s,
                )
            ) is not None:
                struct = self.parse_renamed_attr_dtype(
                    struct,
                    m.group(1),
                    m.group(2),
                    m.group(3),
                )
            elif (
                m := re.match(r"([A-Za-z0-9_]+)\s*:\s*([A-Za-z0-9]+)", s)
            ) is not None:
                struct = self.parse_attr_dtype(struct, m.group(1), m.group(2))
            elif (m := re.match(r"([A-Za-z0-9]+)", s)) is not None:
                struct = self.parse_lone_dtype(struct, m.group(1))
            elif (m := re.match(r"[(\[{<]", s)) is not None:
                self.parse_opening_delimiter()
            elif (m := re.match(r"[)\]}>]", s)) is not None:
                struct = self.parse_closing_delimiter(struct)
            elif (m := re.match(r"[,\n\s]+", s)) is not None:
                pass
            else:
                raise SchemaParsingError(self.format_error(s))

            # clean up the current match
            s = s.replace(m.group(0), "", 1)

        # clean up in case someone checks the object attributes
        delattr(self, "record")

        # build the final object
        self.struct = pl.Struct(struct)

        return self.struct


class DuplicateColumnError(Exception):
    """When a column is encountered more than once in the schema."""


class PathRenamingError(Exception):
    """When a parent (in a JSON path sense) is being renamed."""


class SchemaParsingError(Exception):
    """When unexpected content is encountered and cannot be parsed."""


class UnknownDataTypeError(Exception):
    """When an unknown/unsupported datatype is encountered."""


@pl.api.register_dataframe_namespace("json")
@pl.api.register_lazyframe_namespace("json")
class UnpackFrame:
    """Register a new `df.json.unpack()` method onto `Polars` objects."""

    def __init__(self, df: pl.DataFrame | pl.LazyFrame, separator: str = ".") -> None:
        """Instantiate the object.

        Parameters
        ----------
        df : pl.DataFrame | pl.LazyFrame
            `Polars` `DataFrame` or `LazyFrame` object to unpack.
        separator : str
            JSON path separator to use when building the full JSON path.

        """
        self._df: pl.DataFrame | pl.LazyFrame = df
        self.separator: str = separator

    def unpack(
        self,
        dtype: pl.DataType,
        json_path: str = "",
        column: str | None = None,
    ) -> pl.DataFrame | pl.LazyFrame:
        """Unpack JSON content into a `DataFrame` (or `LazyFrame`) given a schema.

        Parameters
        ----------
        dtype : polars.DataType
            Datatype of the current object (`polars.Array`, `polars.List` or
            `polars.Struct`).
        json_path : str
            Full JSON path (_aka_ breadcrumbs) to the current field.
        column : str | None
            Column to apply the unpacking on; defaults to `None`. This is used when the
            current object has children but no field name; this is the case for
            convoluted `polars.List` within a `polars.List` for instance.

        Returns
        -------
        : polars.DataFrame | polars.LazyFrame
            Updated [unpacked] `Polars` `DataFrame` (or `LazyFrame`) object.

        Notes
        -----
        * The `polars.Array` is considered the [obsolete] ancestor of `polars.List` and
          expected to behave identically.
        * Unpacked columns will be renamed as their full respective JSON paths to avoid
          potential identical names.

        """
        # if we are dealing with a nesting column
        if column is not None:
            if dtype in (pl.Array, pl.List):
                # rename column to json path
                jp = f"{json_path}{self.separator}{column}".lstrip(self.separator)
                if column in self._df.columns:
                    self._df = self._df.rename({column: jp})
                # unpack
                self._df = self._df.explode(jp).json.unpack(dtype.inner, jp, jp)
            elif dtype == pl.Struct:
                self._df = self._df.unnest(column).json.unpack(dtype, json_path)

        # unpack nested children columns when encountered
        elif hasattr(dtype, "fields"):
            for f in dtype.fields:
                # rename column to json path
                jp = f"{json_path}{self.separator}{f.name}".lstrip(self.separator)
                if f.name in self._df.columns:
                    self._df = self._df.rename({f.name: jp})
                # unpack
                if type(f.dtype) in (pl.Array, pl.List):
                    self._df = self._df.explode(jp).json.unpack(f.dtype.inner, jp, jp)
                elif type(f.dtype) == pl.Struct:
                    self._df = self._df.unnest(jp).json.unpack(f.dtype, jp)

        return self._df


if __name__ == "__main__":
    # infer schema from ndjson
    if len(sys.argv[1:]) == 1 and sys.argv[1].endswith("ndjson"):
        sys.stdout.write(f"{infer_schema(sys.argv[1])}\n")
    # unpack ndjson given a schema; at the end as plain text fits the use case better...
    elif len(sys.argv[1:]) == 2:
        sys.stdout.write(f"{unpack_text(sys.argv[1], sys.argv[2]).fetch(3)}\n")
    # usage
    else:
        sys.stderr.write(f"Usage: python3.1X {sys.argv[0]} <SCHEMA> <NDJSON>\n")

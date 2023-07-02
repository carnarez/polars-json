# Module `unpack`

Automatic JSON unpacking to [`Polars`](https://pola.rs) `DataFrame`.

> _Welcome to my little experiment._

The use case is as follows:

- Provide a schema written in plain text describing the JSON content, to be converted
  into a `Polars` `Struct` (see samples in this repo for examples).
- Read the JSON content (as plain text using `scan_csv()` for instance, or directly as
  JSON via `scan_ndjson()`) and automagically unpack the nested content by processing
  the schema.

A few extra points:

- The schema should be dominant and we should rename fields as they are being unpacked
  to avoid identical names for different columns (which is forbidden by `Polars` for
  obvious reasons).
- Why not using the inferred schema? Because at times we need to provide fields that
  might _not_ be in the JSON file to fit a certain data structure, or simply ignore part
  of the JSON data when unpacking to avoid wasting resources. Oh, and to rename fields
  too.
- It seems `Polars` only accepts input starting with `{`, but not `[` (such as a JSON
  list); although it _is_ valid in a JSON sense...

The current working state of this little DIY can be checked (in `Docker`) via:

```shell
$ make env
> python unpack.py samples/complex.schema samples/complex.ndjson
```

Note that a call of the same script _without_ providing a schema returns a
representation of the latter as _inferred_ by `Polars` (works as an example of the
syntax used to describe things in plain text):

```shell
$ make env
> python unpack.py samples/complex.ndjson
```

A thorough(-ish) battery of tests can be performed (in `Docker`) via:

```shell
$ make test
```

Although testing various functionalities, these tests are pretty independent. But the
`test_real_life()` functions working on a common example
([schema](/samples/complex.schema) & [data](/samples/complex.ndjson)) are there to check
if this is only fantasy. Running is convincing!

Feel free to extend the functionalities to your own use case.

**Functions**

- [`infer_schema()`](#unpackinfer_schema): Lazily scan newline-delimited JSON data and
  print the `Polars`-inferred schema.
- [`parse_schema()`](#unpackparse_schema): Parse a plain text JSON schema into a
  `Polars` `Struct`.
- [`unpack_frame()`](#unpackunpack_frame): Unpack a \[nested\] JSON into a `Polars`
  `DataFrame` or `LazyFrame` given a schema.
- [`unpack_ndjson()`](#unpackunpack_ndjson): Lazily scan and unpack newline-delimited
  JSON file given a `Polars` schema.
- [`unpack_text()`](#unpackunpack_text): Lazily scan and unpack JSON data read as plain
  text, given a `Polars` schema.

**Classes**

- [`SchemaParser`](#unpackschemaparser): Parse a plain text JSON schema into a `Polars`
  `Struct`.
- [`DuplicateColumnError`](#unpackduplicatecolumnerror): When a column is encountered
  more than once in the schema.
- [`PathRenamingError`](#unpackpathrenamingerror): When a parent (in a JSON path sense)
  is being renamed.
- [`SchemaParsingError`](#unpackschemaparsingerror): When unexpected content is
  encountered and cannot be parsed.
- [`UnknownDataTypeError`](#unpackunknowndatatypeerror): When an unknown/unsupported
  datatype is encountered.

## Functions

### `unpack.infer_schema`

```python
infer_schema(path_data: str) -> str:
```

Lazily scan newline-delimited JSON data and print the `Polars`-inferred schema.

We expect the following example JSON:

```json
{ "attribute": "test", "nested": { "foo": 1.23, "bar": -8, "vector": [ 0, 1, 2 ] } }
```

to translate into the given `Polars` schema:

```
attribute: Utf8
nested: Struct(
    foo: Float32
    bar: Int16
    vector: List(UInt8)
)
```

Although this merely started as a test for the output of the schema parser defined
somewhere below in this very script, it became quite useful to get a head start when
writing a schema by hand.

**Parameters**

- `path_data` \[`str`\]: Path to a JSON file for `Polars` to infer its own schema
  (_e.g._, `Struct` object).

**Returns**

- \[`str`\]: Pretty-printed `Polars` JSON schema.

### `unpack.parse_schema`

```python
parse_schema(path_schema: str) -> pl.Struct:
```

Parse a plain text JSON schema into a `Polars` `Struct`.

**Parameters**

- `path_schema` \[`str`\]: Path to the plain text file describing the JSON schema.

**Returns**

- \[`polars.Struct`\]: JSON schema translated into `Polars` datatypes.

### `unpack.unpack_frame`

```python
unpack_frame(
    df: pl.DataFrame | pl.LazyFrame,
    dtype: pl.DataType,
    json_path: str = "",
    column: str | None = None,
) -> pl.DataFrame | pl.LazyFrame:
```

Unpack a \[nested\] JSON into a `Polars` `DataFrame` or `LazyFrame` given a schema.

**Parameters**

- `df` \[`polars.DataFrame | polars.LazyFrame`\]: Current `Polars` `DataFrame` (or
  `LazyFrame`) object.
- `dtype` \[`polars.DataType`\]: Datatype of the current object (`polars.Array`,
  `polars.List` or `polars.Struct`).
- `json_path` \[`str`\]: Full JSON path (_aka_ breadcrumbs) to the current field.
- `column` \[`str | None`\]: Column to apply the unpacking on; defaults to `None`. This
  is used when the current object has children but no field name; this is the case for
  convoluted `polars.List` within a `polars.List` for instance.

**Returns**

- \[`polars.DataFrame | polars.LazyFrame`\]: Updated \[unpacked\] `Polars` `DataFrame`
  (or `LazyFrame`) object.

**Notes**

- The `polars.Array` is considered the \[obsolete\] ancestor of `polars.List` and
  expected to behave identically.
- Unpacked columns will be renamed as their full respective JSON paths to avoid
  potential identical names.

### `unpack.unpack_ndjson`

```python
unpack_ndjson(path_schema: str, path_data: str) -> pl.LazyFrame:
```

Lazily scan and unpack newline-delimited JSON file given a `Polars` schema.

**Parameters**

- `path_schema` \[`str`\]: Path to the plain text schema describing the JSON content.
- `path_data` \[`str`\]: Path to the JSON file (or multiple files via glob patterns).

**Returns**

- \[`polars.LazyFrame`\]: Unpacked JSON content, lazy style.

**Notes**

- Fields described in the schema but absent from the JSON source will be added as `null`
  values.
- Fields present in the JSON source but absent from the schema will be dropped.

### `unpack.unpack_text`

```python
unpack_text(path_schema: str, path_data: str, separator: str = "|") -> pl.LazyFrame:
```

Lazily scan and unpack JSON data read as plain text, given a `Polars` schema.

**Parameters**

- `path_schema` \[`str`\]: Path to the plain text schema describing the JSON content.
- `path_data` \[`str`\]: Path to the JSON file (or multiple files via glob patterns).
- `separator` \[`str`\]: Separator to use when parsing the JSON file as a CSV; defaults
  to `|` but `#` or `$` could be good candidates too. Note this separator should \*NOT\*
  be present in the file at all (`,` or `:` are thus out of scope given the JSON
  context). Otherwise... UTF-8 characters?

**Returns**

- \[`polars.LazyFrame`\]: Unpacked JSON content, lazy style.

**Notes**

This is mostly a test, to verify the output would be identical, as this unpacking use
case could be applied on a CSV column containing some JSON content for instance. The
preferred way for native JSON content remains the `unpack_ndjson()` function defined in
this same script.

In the current `Polars` implementation this function is however better suited for the
use case: the provided schema is always dominant, regardless of the content of the JSON
file. We do not need to add or remove missing or supplementary columns, everything is
taken care of by the `json_extract()` method.

## Classes

### `unpack.SchemaParser`

Parse a plain text JSON schema into a `Polars` `Struct`.

**Methods**

- [`format_error()`](#unpackschemaparserformat_error): Format the message printed in the
  exception when an issue occurs.
- [`parse_renamed_attr_dtype()`](#unpackschemaparserparse_renamed_attr_dtype): Parse and
  register an attribute, its new name, and its associated datatype.
- [`parse_attr_dtype()`](#unpackschemaparserparse_attr_dtype): Parse and register an
  attribute and its associated datatype.
- [`parse_lone_dtype()`](#unpackschemaparserparse_lone_dtype): Parse and register a
  standalone datatype (found within a list for instance).
- [`parse_opening_delimiter()`](#unpackschemaparserparse_opening_delimiter): Parse and
  register the opening of a nested structure.
- [`parse_closing_delimiter()`](#unpackschemaparserparse_closing_delimiter): Parse and
  register the closing of a nested structure.
- [`to_struct()`](#unpackschemaparserto_struct): Parse the plain text schema into a
  `Polars` `Struct`.

#### Constructor

```python
SchemaParser(source: str = "")
```

Instantiate the object.

**Parameters**

- `source` \[`str`\]: JSON schema described in plain text, using `Polars` datatypes.
  Defaults to an empty string (`""`).

**Attributes**

- `columns` \[`list[str]`\]: Expected list of columns in the final `Polars` `DataFrame`
  or `LazyFrame`.
- `dtypes` \[`list[polars.DataType]`\]: Expected list of datatypes in the final `Polars`
  `DataFrame` or `LazyFrame`.
- `json_paths` \[`dit[str, str]`\]: Dictionary of JSON path -> column name pairs.
- `source` \[`str`\]: JSON schema described in plain text, using `Polars` datatypes.
- `struct` \[`polars.Struct`\]: Plain text schema parsed as a `Polars` `Struct`.

#### Methods

##### `unpack.SchemaParser.format_error`

```python
format_error(unparsed: str) -> str:
```

Format the message printed in the exception when an issue occurs.

```
Tripped on line 2

     1 │ headers: Struct(
     2 │     timestamp: Foo
     ? │                ^^^
```

**Parameters**

- `unparsed` \[`str`\]: State of the unparsed JSON schema; the issue is expected at the
  first line.

**Returns**

- \[`str`\]: Clean and helpful error message, helpfully.

**Notes**

- In most cases this method will look for the first occurrence of the string that raised
  the exception; and it might not be the _actual_ line that did so.
- This method is absolutely useless and could be removed.

##### `unpack.SchemaParser.parse_renamed_attr_dtype`

```python
parse_renamed_attr_dtype(
    struct: pl.Struct,
    name: str,
    renamed_to: str,
    dtype: str,
) -> pl.Struct:
```

Parse and register an attribute, its new name, and its associated datatype.

**Parameters**

- `struct` \[`polars.Struct`\]: Current state of the `Polars` `Struct`.
- `name` \[`str`\]: Current attribute name.
- `renamed_to` \[`str`\]: New name for the attribute.
- `dtype` \[`str`\]: Expected `Polars` datatype for this attribute.

**Returns**

- \[`polars.Struct`\]: Updated `Polars` `Struct` including the latest parsed addition.

**Raises**

- \[`DuplicateColumnError`\]: When a column is encountered more than once in the schema.
- \[`UnknownDataTypeError`\]: When an unknown/unsupported datatype is encountered.

##### `unpack.SchemaParser.parse_attr_dtype`

```python
parse_attr_dtype(struct: pl.Struct, name: str, dtype: str) -> pl.Struct:
```

Parse and register an attribute and its associated datatype.

**Parameters**

- `struct` \[`polars.Struct`\]: Current state of the `Polars` `Struct`.
- `name` \[`str`\]: Attribute name.
- `dtype` \[`str`\]: Expected `Polars` datatype for this attribute.

**Returns**

- \[`polars.Struct`\]: Updated `Polars` `Struct` including the latest parsed addition.

**Raises**

- \[`DuplicateColumnError`\]: When a column is encountered more than once in the schema.
- \[`UnknownDataTypeError`\]: When an unknown/unsupported datatype is encountered.

##### `unpack.SchemaParser.parse_lone_dtype`

```python
parse_lone_dtype(struct: pl.Struct, dtype: str) -> pl.Struct:
```

Parse and register a standalone datatype (found within a list for instance).

**Parameters**

- `struct` \[`polars.Struct`\]: Current state of the `Polars` `Struct`.
- `dtype` \[`str`\]: Expected `Polars` datatype.

**Returns**

- \[`polars.Struct`\]: Updated `Polars` `Struct` including the latest parsed addition.

**Raises**

- \[`UnknownDataTypeError`\]: When an unknown/unsupported datatype is encountered.

##### `unpack.SchemaParser.parse_opening_delimiter`

```python
parse_opening_delimiter() -> None:
```

Parse and register the opening of a nested structure.

##### `unpack.SchemaParser.parse_closing_delimiter`

```python
parse_closing_delimiter(struct: pl.Struct) -> pl.Struct:
```

Parse and register the closing of a nested structure.

**Parameters**

- `struct` \[`polars.Struct`\]: Current state of the `Polars` `Struct`.

**Returns**

- \[`polars.Struct`\]: Updated `Polars` `Struct` including the latest parsed addition.

##### `unpack.SchemaParser.to_struct`

```python
to_struct() -> pl.Struct:
```

Parse the plain text schema into a `Polars` `Struct`.

We expect something as follows:

```
attribute: Utf8
nested: Struct(
    foo: Float32
    bar=bax: Int16
    vector: List[UInt8]
)
```

to translate into a `Polars` native `Struct` object:

```python
polars.Struct([
    polars.Field("attribute", polars.Utf8),
    polars.Struct([
        polars.Field("foo", polars.Float32),
        polars.Field("bar", polars.Int16),
        polars.Field("vector", polars.List(polars.UInt8))
    ])
])
```

The following patterns (recognised via regular expressions) are supported:

- `([A-Za-z0-9_]+)\s*=\s*([A-Za-z0-9_]+)\s*:\s*([A-Za-z0-9]+)` for an attribute name, an
  equal sign (`=`), a new name for the attribute, a column (`:`) and a datatype.
  Attribute name and datatype must not have spaces and only include alphanumerical or
  underscore (`_`) characters.
- `([A-Za-z0-9_]+)\s*:\s*([A-Za-z0-9]+)` for an attribute name, a column (`:`) and a
  datatype; for instance `attribute: Utf8` in the example above.
- `([A-Za-z0-9]+)` for a lone datatype; for instance the inner content of the `List()`
  in the example above. Keep in mind this datatype could be a complex structure as much
  as a canonical datatype.
- `[(\[{<]` and its `[)\]}>]` counterpart for opening and closing of nested datatypes.
  Any of these characters can be used to open or close nested structures; mixing also
  allowed, for the better or the worse.

Indentation and trailing commas are ignored. The source is parsed until the end of the
file is reached or a `SchemaParsingError` exception is raised.

**Returns**

- \[`polars.Struct`\]: Plain text schema parsed as a `Polars` `Struct`.

**Raises**

- \[`SchemaParsingError`\]: When unexpected content is encountered and cannot be parsed.

### `unpack.DuplicateColumnError`

When a column is encountered more than once in the schema.

#### Constructor

```python
DuplicateColumnError()
```

### `unpack.PathRenamingError`

When a parent (in a JSON path sense) is being renamed.

#### Constructor

```python
PathRenamingError()
```

### `unpack.SchemaParsingError`

When unexpected content is encountered and cannot be parsed.

#### Constructor

```python
SchemaParsingError()
```

### `unpack.UnknownDataTypeError`

When an unknown/unsupported datatype is encountered.

#### Constructor

```python
UnknownDataTypeError()
```

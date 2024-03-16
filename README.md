With this little experiment we tried to increase the capabilities offered by
[`Polars`](https://pola.rs) with the introduction of both a JSON schema parser, and an
automated unpacking method available for both `DataFrame` or `LazyFrame`.

The initial use case can be succinctly illustrated as follows: by providing a schema
written in the following `Polars`-flavoured pseudo-code...

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

the newline-delimited JSON file defined below...

```json
{ "column": "content", "nested": [ { "attr": 0, "attr2": 2 }, { "attr": 1, "attr2": 3 } ], "omitted_in_schema": "ignored" }
```

gets automatically unpacked (via the `.json.unpack(schema)` method) as...

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

Note the renaming syntax as well as the missing and extra attributes, and what this all
means for the final `Polars` object. More
[convoluted examples](https://github.com/carnarez/polars-unpack/tree/master/tests/samples)
are provided in the repo.

Both the parser and the definition of the `.json.unpack()` method are contained in a 
single module. Make this one available on your system via a simple:

```shell
$ pip install git+https://github.com/carnarez/polars-unpack@master
```

or:

```shell
$ wget https://raw.githubusercontent.com/carnarez/polars-unpack/master/polars_unpack/unpack.py
```

for the module itself; whichever you find more appropriate and/or adapted to your usage.
From there it is as usual:

```python
import polars as pl

from polars_unpack import (
    SchemaParser,
    UnpackFrame,  # imported to register the .json.unpack() method
)

# define the schema object
s = SchemaParser(
    "column: String "
    "nested: List(Struct(attr: UInt8,attr2=renamed: UInt8)) "
    "missing_from_source: Float32 "
)

# parse the schema and register json paths associated with final column names
s.to_struct()

# read as plain text using the lazy scan_csv() method before unpacking the data and
# renaming its fields to their final name (renamed during unpacking to their full
# respective json paths to avoid column naming collisions)
df = (
    pl.scan_csv(
        "**.ndjson",
        has_header=False,
        new_columns=["raw"],
        separator="|",  # or any other character *absent* from the raw data
    )
    .select(pl.col("raw").str.json_extract(s.struct))
    .unnest("raw")
    .json.unpack(s.struct)  # registered within the *frame namespaces
    .rename(s.json_paths)
)
```

If your schema and JSON are stored as plain files the result above can be reached using
any of the following helper functions:

```python
import polars as pl

from polars_unpack import unpack_text
from polars_unpack import unpack_ndjson

df = unpack_text("**.ndjson", "file.schema")
df = unpack_ndjson("**.ndjson", "file.schema")
```

Note that these functions are using `scan_csv()` and `scan_ndjson()` respectively; any
extra parameters passed to `unpack_text()` or `unpack_ndjson()` functions will be
forwarded to these methods (with the exception of the `separator` argument, read the
docstring of `unpack_text()` for more information).

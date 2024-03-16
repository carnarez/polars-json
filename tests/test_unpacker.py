"""Assert capabilities of the `DataFrame` / `LazyFrame` flattener."""

import json

import polars as pl
import pytest

from polars_unpack import SchemaParser, unpack_ndjson, unpack_text


def test_datatype() -> None:
    """Test a standalone datatype.

    Test the following JSON content:

    ```json
    1
    ```

    as described by the following schema:

    ```
    Int64
    ```
    """
    dtype = pl.Struct(
        [
            pl.Field("", pl.Int64),
        ],
    )

    df = pl.DataFrame([0, 1, 2, 3], dtype)

    # tested in the other module but might as well...
    assert SchemaParser("Int64").to_struct() == dtype
    assert dtype.to_schema() == df.schema
    assert df.json.unpack(dtype).equals(df)


def test_list() -> None:
    """Test a simple `polars.List` containing a standalone datatype.

    Test the following nested JSON content:

    ```json
    {
        "text": "foobar",
        "json": [
            0,
            1,
            2,
            3
        ]
    }
    ```

    as described by the following schema:

    ```
    text: String,
    json: List(Int64)
    ```
    """
    dtype = pl.Struct(
        [
            pl.Field("text", pl.String),
            pl.Field("json", pl.List(pl.Int64)),
        ],
    )

    df = pl.DataFrame(
        {
            "text": "foobar",
            "json": json.loads("[[0, 1, 2, 3]]"),
        },
        dtype,
    )

    assert SchemaParser("text:String,json:List(Int64)").to_struct() == dtype
    assert dtype.to_schema() == df.schema
    assert df.json.unpack(dtype).equals(df.explode("json"))


def test_list_nested_in_list_nested_in_list() -> None:
    """Test a `polars.List` nested in parent `polars.List`s.

    Test the following nested JSON content:

    ```json
    {
        "text": "foobar",
        "json": [
            [
                [
                    [10, 12],
                    [11, 13]
                ],
                [
                    [30, 32],
                    [31, 33]
                ]
            ],
            [
                [
                    [20, 22],
                    [21, 23]
                ],
                [
                    [40, 42],
                    [41, 43]
                ]
            ]
        ]
    }
    ```

    as described by the following schema:

    ```
    text: String,
    json: List(List(List(Int64)))
    ```
    """
    dtype = pl.Struct(
        [
            pl.Field("text", pl.String),
            pl.Field(
                "json",
                pl.List(
                    pl.List(
                        pl.List(pl.Int64),
                    ),
                ),
            ),
        ],
    )

    df = pl.DataFrame(
        {
            "text": "foobar",
            "json": json.loads(
                "[[[[10, 12], [11, 13]], [[30, 32], [31, 33]]],"
                " [[[20, 22], [21, 23]], [[40, 42], [41, 43]]]]",
            ),
        },
        dtype,
    )

    assert SchemaParser("text:String,json:List(List(List(Int64)))").to_struct() == dtype
    assert dtype.to_schema() == df.schema
    assert (
        df.json.unpack(dtype)
        .rename({"json.json.json.json": "json"})
        .equals(
            df.explode("json").explode("json").explode("json"),
        )
    )


def test_list_nested_in_struct() -> None:
    """Test a `polars.List` nested in a `polars.Struct`.

    Test the following nested JSON content:

    ```json
    {
        "text": "foobar",
        "json": {
            "foo": {
                "fox": 0,
                "foz": 2
            },
            "bar": [
                1,
                3
            ]
        }
    }
    ```

    as described by the following schema:

    ```
    text: String,
    json: Struct(
        foo: Struct(
            fox: Int64,
            foz: Int64
        ),
        bar: List(Int64)
    )
    ```
    """
    dtype = pl.Struct(
        [
            pl.Field("text", pl.String),
            pl.Field(
                "json",
                pl.Struct(
                    [
                        pl.Field(
                            "foo",
                            pl.Struct(
                                [pl.Field("fox", pl.Int64), pl.Field("foz", pl.Int64)],
                            ),
                        ),
                        pl.Field("bar", pl.List(pl.Int64)),
                    ],
                ),
            ),
        ],
    )

    df = pl.DataFrame(
        {
            "text": ["foobar"],
            "json": [
                json.loads(
                    '{"foo": {"fox": 0, "foz": 2}, "bar": [1, 3]}',
                ),
            ],
        },
        dtype,
    )

    assert (
        SchemaParser(
            "text:String,json:Struct(foo:Struct(fox:Int64,foz:Int64),bar:List(Int64))",
        ).to_struct()
        == dtype
    )
    assert dtype.to_schema() == df.schema
    assert df.json.unpack(dtype).equals(
        df.unnest("json")
        .unnest("foo")
        .explode("bar")
        .rename({"fox": "json.foo.fox", "foz": "json.foo.foz", "bar": "json.bar"}),
    )


@pytest.mark.parametrize(
    ("df"),
    [
        unpack_ndjson(
            "tests/samples/complex.schema",
            "tests/samples/complex.ndjson",
        ).collect(),
        unpack_text(
            "tests/samples/complex.schema",
            "tests/samples/complex.ndjson",
        ).collect(),
    ],
)
def test_real_life(df: pl.DataFrame) -> None:
    """Test complex real life-like parsing and flattening.

    Test the following nested JSON content:

    ```json
    {
        "headers": {
            "timestamp": 1372182309,
            "source": "Online.Transactions",
            "offset": 123456789,
        },
        "payload": {
            "transaction": "inbound",
            "location": 765,
            "customer": {
                "type": "REGISTERED",
                "identifier": "a8098c1a-f86e-11da-bd1a-00112444be1e"
            },
            "lines": [
                {
                    "product": 76543,
                    "description": "Toilet plunger",
                    "quantity": 2,
                    "vatRate": 0.21,
                    "amount": {
                        "includingVat": 10.0,
                        "excludingVat": 8.26,
                        "vat": 1.74,
                        "currency": "EUR"
                    },
                    "discounts": [
                        {
                            "promotion": 100023456000789,
                            "description": "Buy one get two",
                            "amount": {
                                "includingVat": 10.0,
                                "excludingVat": 8.26,
                                "vat": 1.74,
                                "currency": "EUR"
                            }
                        }
                    ]
                },
                {
                    "product": 3456,
                    "description": "Toilet cap",
                    "quantity": 1,
                    "vatRate": 0.21,
                    "amount": {
                        "includingVat": 30.0,
                        "excludingVat": 24.79,
                        "vat": 5.21,
                        "currency": "EUR"
                    }
                }
            ],
            "payment": {
                "method": "Card",
                "company": "OnlineBanking",
                "identifier": 123456789,
                "amount": {
                    "includingVat": 40.0,
                    "excludingVat": 33.05,
                    "vat": 6.95,
                    "currency": "EUR"
                }
            }
        }
    }
    ```

    as described by the following schema:

    ```
    headers: Struct<
        timestamp: Int64
        source: String
        offset: Int64
    >
    payload: Struct<
        transaction=transaction_type: String
        location: Int64
        customer: Struct{
            type=customer_type: String
            identifier=customer_identifier: String
        }
        lines: List[
            Struct{
                product: Int64
                description=product_description: String
                quantity: Int64
                vatRate=vat_rate: Float64
                amount: Struct(
                    includingVat=line_amount_including_vat: Float64
                    excludingVat=line_amount_excluding_vat: Float64
                    vat=line_amount_vat: Float64
                    currency=line_amount_currency: String
                )
                discounts: List[
                    Struct{
                        promotion: Int64
                        description=promotion_description: String
                        amount: Struct{
                            includingVat=discount_amount_including_vat: Float64
                            excludingVat=discount_amount_excluding_vat: Float64
                            vat=discount_amount_vat: Float64
                            currency=discount_amount_currency: String
                        }
                    }
                ]
            }
        ]
        payment: Struct{
            method: String
            company: String
            identifier=transaction_identifier: Int64
            amount: Struct{
                includingVat=total_amount_including_vat: Float64
                excludingVat=total_amount_excluding_vat: Float64
                vat=total_amount_vat: Float64
                currency=total_amount_currency: String
            }
        }
    >
    ```

    Parameters
    ----------
    df : polars.DataFrame
        Unpacked `Polars` `DataFrame`.

    """
    df_csv = pl.scan_csv(
        "tests/samples/complex.csv",
        dtypes={
            "timestamp": pl.Int64,
            "source": pl.String,
            "offset": pl.Int64,
            "transaction_type": pl.String,
            "location": pl.Int64,
            "customer_type": pl.String,
            "customer_identifier": pl.String,
            "product": pl.Int64,
            "product_description": pl.String,
            "quantity": pl.Int64,
            "vat_rate": pl.Float64,
            "line_amount_including_vat": pl.Float64,
            "line_amount_excluding_vat": pl.Float64,
            "line_amount_vat": pl.Float64,
            "line_amount_currency": pl.String,
            "promotion": pl.Int64,
            "promotion_description": pl.String,
            "discount_amount_including_vat": pl.Float64,
            "discount_amount_excluding_vat": pl.Float64,
            "discount_amount_vat": pl.Float64,
            "discount_amount_currency": pl.String,
            "method": pl.String,
            "company": pl.String,
            "transaction_identifier": pl.Int64,
            "total_amount_including_vat": pl.Float64,
            "total_amount_excluding_vat": pl.Float64,
            "total_amount_vat": pl.Float64,
            "total_amount_currency": pl.String,
        },
    ).collect()

    assert df.dtypes == df_csv.dtypes
    assert df.equals(df_csv)


def test_rename_fields() -> None:
    """Test for `polars.Struct` field renaming according to provided schema.

    Test the following nested JSON content:

    ```json
    {
        "text": "foobar",
        "json": {
            "foo": 0,
            "bar": 1
        }
    }
    ```

    as described by the following schema:

    ```
    text=string: String,
    json: Struct(
        foo=fox: Int64,
        bar=bax: Int64
    )
    ```

    which should return:

    ```
    ┌────────┬─────┬─────┐
    │ string ┆ fox ┆ bax │
    │ ---    ┆ --- ┆ --- │
    │ str    ┆ i64 ┆ i64 │
    ╞════════╪═════╪═════╡
    │ foobar ┆ 0   ┆ 1   │
    └────────┴─────┴─────┘
    ```
    """
    # schema parsing
    schema = SchemaParser("text=string:String,json:Struct(foo=fox:Int64,bar=bax:Int64)")
    schema.to_struct()

    # original dataframe
    dtype = pl.Struct(
        [
            pl.Field("text", pl.String),
            pl.Field(
                "json",
                pl.Struct([pl.Field("foo", pl.Int64), pl.Field("bar", pl.Int64)]),
            ),
        ],
    )

    df = pl.DataFrame(
        {
            "text": ["foobar"],
            "json": [json.loads('{"foo": 0, "bar": 1}')],
        },
        dtype,
    )

    # renamed dataframe
    dtype_renamed = pl.Struct(
        [
            pl.Field("string", pl.String),
            pl.Field(
                "json",
                pl.Struct([pl.Field("fox", pl.Int64), pl.Field("bax", pl.Int64)]),
            ),
        ],
    )

    df_renamed = pl.DataFrame(
        {
            "string": ["foobar"],
            "json": [json.loads('{"fox": 0, "bax": 1}')],
        },
        dtype_renamed,
    )

    assert (
        df.json.unpack(dtype)
        .rename(schema.json_paths)
        .equals(df_renamed.unnest("json"))
    )


def test_struct() -> None:
    """Test a simple `polars.Struct` containing a few fields.

    Test the following nested JSON content:

    ```json
    {
        "text": "foobar",
        "json": {
            "foo": 0,
            "bar": 1
        }
    }
    ```

    as described by the following schema:

    ```
    text: String,
    json: Struct(
        foo: Int64,
        bar: Int64
    )
    ```
    """
    dtype = pl.Struct(
        [
            pl.Field("text", pl.String),
            pl.Field(
                "json",
                pl.Struct([pl.Field("foo", pl.Int64), pl.Field("bar", pl.Int64)]),
            ),
        ],
    )

    df = pl.DataFrame(
        {
            "text": ["foobar"],
            "json": [json.loads('{"foo": 0, "bar": 1}')],
        },
        dtype,
    )

    assert (
        SchemaParser("text:String,json:Struct(foo:Int64,bar:Int64)").to_struct()
        == dtype
    )
    assert dtype.to_schema() == df.schema
    assert df.json.unpack(dtype).equals(
        df.unnest("json").rename({"foo": "json.foo", "bar": "json.bar"}),
    )


def test_struct_nested_in_list() -> None:
    """Test a `polars.Struct` nested in a `polars.List`.

    Test the following nested JSON content:

    ```json
    {
        "text": "foobar",
        "json": [
            {
                "foo": 0,
                "bar": 1
            },
            {
                "foo": 2,
                "bar": 3
            }
        ]
    }
    ```

    as described by the following schema:

    ```
    text: String,
    json: List(
        Struct(
            foo: Int64,
            bar: Int64
        )
    )
    ```
    """
    dtype = pl.Struct(
        [
            pl.Field("text", pl.String),
            pl.Field(
                "json",
                pl.List(
                    pl.Struct([pl.Field("foo", pl.Int64), pl.Field("bar", pl.Int64)]),
                ),
            ),
        ],
    )

    df = pl.DataFrame(
        {
            "text": "foobar",
            "json": json.loads('[[{"foo": 0, "bar": 1}, {"foo": 2, "bar": 3}]]'),
        },
        dtype,
    )

    assert (
        SchemaParser("text:String,json:List(Struct(foo:Int64,bar:Int64))").to_struct()
        == dtype
    )
    assert dtype.to_schema() == df.schema
    assert df.json.unpack(dtype).equals(
        df.explode("json")
        .unnest("json")
        .rename({"foo": "json.foo", "bar": "json.bar"}),
    )


def test_struct_nested_in_struct() -> None:
    """Test a `polars.Struct` nested within another `polars.Struct`.

    Test the following nested JSON content:

    ```json
    {
        "text": "foobar",
        "json": {
            "foo": {
                "fox": 0,
                "foz": 2
            },
            "bar": {
                "bax": 1,
                "baz": 3
            }
        }
    }
    ```

    as described by the following schema:

    ```
    text: String,
    json: Struct(
        foo: Struct(
            fox: Int64,
            foz: Int64
        ),
        bar: Struct(
            bax: Int64,
            baz: Int64
        )
    )
    ```
    """
    # yup, this is why we want this to be generated
    dtype = pl.Struct(
        [
            pl.Field("text", pl.String),
            pl.Field(
                "json",
                pl.Struct(
                    [
                        pl.Field(
                            "foo",
                            pl.Struct(
                                [pl.Field("fox", pl.Int64), pl.Field("foz", pl.Int64)],
                            ),
                        ),
                        pl.Field(
                            "bar",
                            pl.Struct(
                                [pl.Field("bax", pl.Int64), pl.Field("baz", pl.Int64)],
                            ),
                        ),
                    ],
                ),
            ),
        ],
    )

    df = pl.DataFrame(
        {
            "text": ["foobar"],
            "json": [
                json.loads(
                    '{"foo": {"fox": 0, "foz": 2}, "bar": {"bax": 1, "baz": 3}}',
                ),
            ],
        },
        dtype,
    )

    assert (
        SchemaParser(
            "text:String,"
            "json:Struct(foo:Struct(fox:Int64,foz:Int64),bar:Struct(bax:Int64,baz:Int64))",
        ).to_struct()
        == dtype
    )
    assert dtype.to_schema() == df.schema
    assert df.json.unpack(dtype).equals(
        df.unnest("json")
        .unnest("foo", "bar")
        .rename(
            {
                "fox": "json.foo.fox",
                "foz": "json.foo.foz",
                "bax": "json.bar.bax",
                "baz": "json.bar.baz",
            },
        ),
    )

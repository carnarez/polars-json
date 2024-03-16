"""Assert capabilities of the schema parser."""

import pathlib

import polars as pl
import pytest

from polars_unpack import (
    POLARS_DATATYPES,
    DuplicateColumnError,
    PathRenamingError,
    SchemaParser,
    SchemaParsingError,
    UnknownDataTypeError,
    infer_schema,
    parse_schema,
)


@pytest.mark.parametrize(
    ("text", "struct"),
    [
        (text.capitalize(), pl.Struct([pl.Field("", dtype)]))
        for text, dtype in POLARS_DATATYPES.items()
        if text not in ("list", "struct")
    ],
)
def test_datatype(text: str, struct: pl.Struct) -> None:
    """Test all supported standalone non-nesting datatypes and associated shorthands.

    Parameters
    ----------
    text : str
        Schema in plain text.
    struct : polars.Struct
        Expected datatype.

    """
    assert SchemaParser(text).to_struct() == struct


@pytest.mark.parametrize(
    ("text", "struct"),
    [
        (
            "List(Int8)",
            pl.Struct([pl.List(pl.Int8)]),
        ),
        (
            "Struct(foo: Int8, bar: Int8)",
            pl.Struct(
                [
                    pl.Field(
                        "",
                        pl.Struct([pl.Field("foo", pl.Int8), pl.Field("bar", pl.Int8)]),
                    ),
                ],
            ),
        ),
    ],
)
def test_datatype_nested(text: str, struct: pl.Struct) -> None:
    """Test nesting datatypes.

    Parameters
    ----------
    text : str
        Schema in plain text.
    struct : polars.Struct
        Expected datatype.

    """
    assert SchemaParser(text).to_struct() == struct


@pytest.mark.parametrize(
    ("text", "struct"),
    [
        (
            "Struct(foo: Int8)",
            pl.Struct([pl.Field("", pl.Struct([pl.Field("foo", pl.Int8)]))]),
        ),
        (
            "Struct[foo: Int8]",
            pl.Struct([pl.Field("", pl.Struct([pl.Field("foo", pl.Int8)]))]),
        ),
        (
            "Struct{foo: Int8}",
            pl.Struct([pl.Field("", pl.Struct([pl.Field("foo", pl.Int8)]))]),
        ),
        (
            "Struct<foo: Int8>",
            pl.Struct([pl.Field("", pl.Struct([pl.Field("foo", pl.Int8)]))]),
        ),
        (
            "Struct(foo: String]",  # mixed!?
            pl.Struct([pl.Field("", pl.Struct([pl.Field("foo", pl.String)]))]),
        ),
    ],
)
def test_delimiter(text: str, struct: pl.Struct) -> None:
    """Test nested structure delimiters: `()`, `[]`, `{}` or `<>`.

    Parameters
    ----------
    text : str
        Schema in plain text.
    struct : polars.Struct
        Expected datatype.

    """
    assert SchemaParser(text).to_struct() == struct


def test_list_nested_in_list() -> None:
    """Test the parsing of a `polars.List` within a `polars.List`.

    Test the generation of the following schema:

    ```
    List(List(Int8))
    ```
    """
    struct = pl.Struct([pl.List(pl.List(pl.Int8))])

    assert SchemaParser("List(List(Int8))").to_struct() == struct


def test_list_nested_in_struct() -> None:
    """Test the parsing of a `polars.List` within a `polars.Struct`.

    Test the generation of the following schema:

    ```
    Struct(
        foo: List(Int8)
    )
    ```
    """
    struct = pl.Struct([pl.Field("", pl.Struct([pl.Field("foo", pl.List(pl.Int8))]))])

    assert SchemaParser("Struct(foo: List(Int8))").to_struct() == struct


def test_pretty_printing() -> None:
    """Test whether an inferred schema is correctly printed."""
    with pathlib.Path("tests/samples/nested-list.schema").open() as f:
        assert infer_schema("tests/samples/nested-list.ndjson") == f.read().strip()


def test_real_life() -> None:
    """Test complex schema.

    Test the following nested JSON content:

    ```json
    {
        "headers": {
            "timestamp": 1372182309,
            "source": "Online.Transactions",
            "offset": 123456789
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
                includingVat=total_amount_including_vat: Float32
                excludingVat=total_amount_excluding_vat: Float32
                vat=total_amount_vat: Float32
                currency=total_amount_currency: String
            }
        }
    >
    ```
    """
    dtype = parse_schema("tests/samples/complex.schema").struct
    df = pl.scan_ndjson("tests/samples/complex.ndjson").collect()

    assert dtype.to_schema() == df.schema


def test_struct_nested_in_list() -> None:
    """Test the parsing of a `polars.Struct` within a `polars.List`.

    Test the generation of the following schema:

    ```
    List(
        Struct(
            foo: Int8,
            bar: Int8
        )
    )
    ```

    Notes
    -----
    It seems `Polars` only accepts input starting with `{`, but not `[` (such as a JSON
    lists); although the schema described above is valid in a JSON sense, the associated
    data will not be ingested by `Polars`.

    """
    struct = pl.Struct(
        [pl.List(pl.Struct([pl.Field("foo", pl.Int8), pl.Field("bar", pl.Int8)]))],
    )

    assert SchemaParser("List(Struct(foo: Int8, bar: Int8))").to_struct() == struct


def test_struct_nested_in_struct() -> None:
    """Test the parsing of a `polars.Struct` within a `polars.Struct`.

    Test the generation of the following schema:

    ```
    Struct(
        foo: Struct(
            bar: Int8
        )
    )
    ```
    """
    struct = pl.Struct(
        [
            pl.Field(
                "",
                pl.Struct([pl.Field("foo", pl.Struct([pl.Field("bar", pl.Int8)]))]),
            ),
        ],
    )

    assert SchemaParser("Struct(foo: Struct(bar: Int8))").to_struct() == struct


def test_unexpected_duplication() -> None:
    """Test for duplicated column name (including after column renaming)."""
    with pytest.raises(DuplicateColumnError):
        SchemaParser("Struct(foo: Int8, foo: Float32)").to_struct()
    with pytest.raises(DuplicateColumnError):
        SchemaParser("Struct(foo: Int8, bar=foo: Float32)").to_struct()


def test_unexpected_renaming() -> None:
    """Test for JSON path renaming (unsupported, and quite useless as well)."""
    with pytest.raises(PathRenamingError):
        SchemaParser("this=that:Struct(foo:Int8)").to_struct()


def test_unexpected_syntax() -> None:
    """Test for failure to parse the schema due to unknown/unexpected syntax."""
    with pytest.raises(SchemaParsingError):
        SchemaParser("!@#$%^&*").to_struct()
    with pytest.raises(SchemaParsingError):
        SchemaParser("Struct(!@#$%^&*)").to_struct()


def test_unknown_datatype() -> None:
    """Test for unknown datatype."""
    with pytest.raises(UnknownDataTypeError):
        SchemaParser("Foo").to_struct()
    with pytest.raises(UnknownDataTypeError):
        SchemaParser("Struct(foo: Bar)").to_struct()
    with pytest.raises(UnknownDataTypeError):
        SchemaParser("Struct(foo=fox: Bar)").to_struct()

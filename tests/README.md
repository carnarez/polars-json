# Module `__init__`

Thorough(-ish) battery of tests for our little unpacking stunt.

# Module `test_parser`

Assert capabilities of the schema parser.

**Functions**

- [`test_datatype()`](#test_parsertest_datatype): Test all supported standalone
  non-nesting datatypes and associated shorthands.
- [`test_datatype_nested()`](#test_parsertest_datatype_nested): Test nesting datatypes.
- [`test_delimiter()`](#test_parsertest_delimiter): Test nested structure delimiters:
  `()`, `[]`, `{}` or `<>`.
- [`test_list_nested_in_list()`](#test_parsertest_list_nested_in_list): Test the parsing
  of a `polars.List` within a `polars.List`.
- [`test_list_nested_in_struct()`](#test_parsertest_list_nested_in_struct): Test the
  parsing of a `polars.List` within a `polars.Struct`.
- [`test_pretty_printing()`](#test_parsertest_pretty_printing): Test whether an inferred
  schema is correctly printed.
- [`test_real_life()`](#test_parsertest_real_life): Test complex schema.
- [`test_struct_nested_in_list()`](#test_parsertest_struct_nested_in_list): Test the
  parsing of a `polars.Struct` within a `polars.List`.
- [`test_struct_nested_in_struct()`](#test_parsertest_struct_nested_in_struct): Test the
  parsing of a `polars.Struct` within a `polars.Struct`.
- [`test_unexpected_duplication()`](#test_parsertest_unexpected_duplication): Test for
  duplicated column name (including after column renaming).
- [`test_unexpected_renaming()`](#test_parsertest_unexpected_renaming): Test for JSON
  path renaming (unsupported, and quite useless as well).
- [`test_unexpected_syntax()`](#test_parsertest_unexpected_syntax): Test for failure to
  parse the schema due to unknown/unexpected syntax.
- [`test_unknown_datatype()`](#test_parsertest_unknown_datatype): Test for unknown
  datatype.

## Functions

### `test_parser.test_datatype`

```python
test_datatype(text: str, struct: pl.Struct) -> None:
```

Test all supported standalone non-nesting datatypes and associated shorthands.

**Parameters**

- `text` \[`str`\]: Schema in plain text.
- `struct` \[`polars.Struct`\]: Expected datatype.

**Decoration** via `@pytest.mark.parametrize()`.

### `test_parser.test_datatype_nested`

```python
test_datatype_nested(text: str, struct: pl.Struct) -> None:
```

Test nesting datatypes.

**Parameters**

- `text` \[`str`\]: Schema in plain text.
- `struct` \[`polars.Struct`\]: Expected datatype.

**Decoration** via `@pytest.mark.parametrize()`.

### `test_parser.test_delimiter`

```python
test_delimiter(text: str, struct: pl.Struct) -> None:
```

Test nested structure delimiters: `()`, `[]`, `{}` or `<>`.

**Parameters**

- `text` \[`str`\]: Schema in plain text.
- `struct` \[`polars.Struct`\]: Expected datatype.

**Decoration** via `@pytest.mark.parametrize()`.

### `test_parser.test_list_nested_in_list`

```python
test_list_nested_in_list() -> None:
```

Test the parsing of a `polars.List` within a `polars.List`.

Test the generation of the following schema:

```
List(List(Int8))
```

### `test_parser.test_list_nested_in_struct`

```python
test_list_nested_in_struct() -> None:
```

Test the parsing of a `polars.List` within a `polars.Struct`.

Test the generation of the following schema:

```
Struct(
    foo: List(Int8)
)
```

### `test_parser.test_pretty_printing`

```python
test_pretty_printing() -> None:
```

Test whether an inferred schema is correctly printed.

### `test_parser.test_real_life`

```python
test_real_life() -> None:
```

Test complex schema.

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

### `test_parser.test_struct_nested_in_list`

```python
test_struct_nested_in_list() -> None:
```

Test the parsing of a `polars.Struct` within a `polars.List`.

Test the generation of the following schema:

```
List(
    Struct(
        foo: Int8,
        bar: Int8
    )
)
```

**Notes**

It seems `Polars` only accepts input starting with `{`, but not `[` (such as a JSON
lists); although the schema described above is valid in a JSON sense, the associated
data will not be ingested by `Polars`.

### `test_parser.test_struct_nested_in_struct`

```python
test_struct_nested_in_struct() -> None:
```

Test the parsing of a `polars.Struct` within a `polars.Struct`.

Test the generation of the following schema:

```
Struct(
    foo: Struct(
        bar: Int8
    )
)
```

### `test_parser.test_unexpected_duplication`

```python
test_unexpected_duplication() -> None:
```

Test for duplicated column name (including after column renaming).

### `test_parser.test_unexpected_renaming`

```python
test_unexpected_renaming() -> None:
```

Test for JSON path renaming (unsupported, and quite useless as well).

### `test_parser.test_unexpected_syntax`

```python
test_unexpected_syntax() -> None:
```

Test for failure to parse the schema due to unknown/unexpected syntax.

### `test_parser.test_unknown_datatype`

```python
test_unknown_datatype() -> None:
```

Test for unknown datatype.

# Module `test_unpacker`

Assert capabilities of the `DataFrame` / `LazyFrame` flattener.

**Functions**

- [`test_datatype()`](#test_unpackertest_datatype): Test a standalone datatype.
- [`test_list()`](#test_unpackertest_list): Test a simple `polars.List` containing a
  standalone datatype.
- [`test_list_nested_in_list_nested_in_list()`](#test_unpackertest_list_nested_in_list_nested_in_list):
  Test a `polars.List` nested in parent `polars.List`s.
- [`test_list_nested_in_struct()`](#test_unpackertest_list_nested_in_struct): Test a
  `polars.List` nested in a `polars.Struct`.
- [`test_real_life()`](#test_unpackertest_real_life): Test complex real life-like
  parsing and flattening.
- [`test_rename_fields()`](#test_unpackertest_rename_fields): Test for `polars.Struct`
  field renaming according to provided schema.
- [`test_struct()`](#test_unpackertest_struct): Test a simple `polars.Struct` containing
  a few fields.
- [`test_struct_nested_in_list()`](#test_unpackertest_struct_nested_in_list): Test a
  `polars.Struct` nested in a `polars.List`.
- [`test_struct_nested_in_struct()`](#test_unpackertest_struct_nested_in_struct): Test a
  `polars.Struct` nested within another `polars.Struct`.

## Functions

### `test_unpacker.test_datatype`

```python
test_datatype() -> None:
```

Test a standalone datatype.

Test the following JSON content:

```json
1
```

as described by the following schema:

```
Int64
```

### `test_unpacker.test_list`

```python
test_list() -> None:
```

Test a simple `polars.List` containing a standalone datatype.

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

### `test_unpacker.test_list_nested_in_list_nested_in_list`

```python
test_list_nested_in_list_nested_in_list() -> None:
```

Test a `polars.List` nested in parent `polars.List`s.

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

### `test_unpacker.test_list_nested_in_struct`

```python
test_list_nested_in_struct() -> None:
```

Test a `polars.List` nested in a `polars.Struct`.

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

### `test_unpacker.test_real_life`

```python
test_real_life(df: pl.DataFrame) -> None:
```

Test complex real life-like parsing and flattening.

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

**Parameters**

- `df` \[`polars.DataFrame`\]: Unpacked `Polars` `DataFrame`.

**Decoration** via `@pytest.mark.parametrize()`.

### `test_unpacker.test_rename_fields`

```python
test_rename_fields() -> None:
```

Test for `polars.Struct` field renaming according to provided schema.

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

### `test_unpacker.test_struct`

```python
test_struct() -> None:
```

Test a simple `polars.Struct` containing a few fields.

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

### `test_unpacker.test_struct_nested_in_list`

```python
test_struct_nested_in_list() -> None:
```

Test a `polars.Struct` nested in a `polars.List`.

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

### `test_unpacker.test_struct_nested_in_struct`

```python
test_struct_nested_in_struct() -> None:
```

Test a `polars.Struct` nested within another `polars.Struct`.

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

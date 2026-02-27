# Pydantic Validation Notes

## Strings and Collections
Use `min_length` and `max_length` for types that have "length." 
- **Types**: `str`, `list`, `tuple`, `set`, `bytes`.
- **Example**: `title: str = Field(..., min_length=2, max_length=100)`

## Numbers
Use comparison operators for numeric types (`int`, `float`, `Decimal`).
- **`ge`**: Greater than or equal to ($\ge$)
- **`le`**: Less than or equal to ($\le$)
- **`gt`**: Greater than ($>$)
- **`lt`**: Less than ($<$)
- **Example**: `age: int = Field(..., ge=18, le=120)`

## Summary Table
| Constraint | Used For | Example |
| :--- | :--- | :--- |
| `min_length` / `max_length` | `str`, `list`, `set`, `tuple`, `bytes` | `min_length=3` |
| `ge` / `le` | `int`, `float`, `Decimal` | `ge=0` |
| `gt` / `lt` | `int`, `float`, `Decimal` | `gt=10` |
| `pattern` | `str` (Regex) | `pattern=r"^[A-Z]+$"` |

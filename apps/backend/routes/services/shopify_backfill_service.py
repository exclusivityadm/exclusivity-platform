async def run_backfill_slice(
  *,
  merchant_id: str,
  shop_domain: str,
  access_token: str,
  points_per_dollar: float,
  cursor: str | None,
  max_pages: int = 5
) -> dict:
  """
  Returns:
    {
      "done": bool,
      "next_cursor": str|None,
      "orders_processed": int,
      "customers_touched": int
    }
  """

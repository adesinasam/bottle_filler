## Bottle Filler App

Bottle Filler App for distribution, wholesale and retail involve in selling refill product.
It tracks returnable empties (RGB bottles, crates, jars) exchanged with customers and suppliers.

### Setup

1. **Empty item** (e.g. *Empty Crate 50CL*, *Empty 20L Jar*): a stock item with a valuation rate.
   - Tick **Is Empty Bottle / Jar**.
   - In **Item Defaults** for each company set the **Default Expense Account**. Every empties
     movement (received from customers, given to suppliers) posts to this account.
     If it is blank the Item Group default is used, then the company's Stock Adjustment Account.
2. **Filled item** (e.g. *Coke 50CL Crate*): tick **Has Empty Bottle**, choose the **Empty Bottle Item**
   and set **Empties per Stock UOM** – how many empty items (in the empty item's stock UOM) go with
   one stock UOM of the filled item. Crate ↔ empty crate = 1; filled stocked per bottle with an empty
   crate of 24 = 0.041666667.

### How it posts

| Voucher | Empties | Stock Entry |
| --- | --- | --- |
| Sales Invoice | customer drops empties | Material Receipt |
| Sales Invoice (return) | empties given back | Material Issue |
| Purchase Invoice | empties given to supplier | Material Issue |
| Purchase Invoice (return) | empties taken back | Material Receipt |
| POS Empty Bottle Entry (Approved) | customer drops empties at POS | Material Receipt |

- **Expected Empties** on each invoice row = filled stock qty × Empties per Stock UOM.
- **Qty (Empty Bottle)** defaults to the expected qty; change it when the party drops more or fewer.
  The difference is kept in the *Empty Bottle Entry* ledger (`difference_in_qty`, positive = shortfall).
- Empties are valued at the empty item's valuation rate.
- **Selling empties** (Sales Invoice, Delivery Note, POS Invoice) is an ordinary sale of the empty
  item; its cost of goods sold goes to the company's **Default Cost of Goods Sold Account**,
  not the empty item's expense account.
- **Buying empties** from a supplier (Purchase Invoice / Purchase Receipt) is an ordinary purchase:
  the empties come into stock at the purchase price and nothing else is posted.
- If empties are sold to / bought from the party **on the same invoice** as filled items, they cover
  that party's shortfall: the ledger shows them as `traded_empty_qty` and the difference drops
  accordingly. Empties bought beyond the shortfall are just a sale/purchase.
- Cancelling the invoice / POS entry cancels its empties Stock Entry.

### Tests

```bash
bench --site <site> run-tests --app bottle_filler
python -m unittest bottle_filler.bottle_filler.tests.test_empties_calc   # no site needed
```

#### License

MIT

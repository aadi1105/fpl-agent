FPL AI — 2026/27 PLAYER-PRICE DATA INTEGRITY AUDIT

Before Phase 3C, perform a full 2026/27 player-price data integrity audit.

IMPORTANT:
Gabriel's incorrect £6.0m price is NOT an isolated issue.

Do NOT hard-code Gabriel's price.

We need to verify that ALL player prices throughout the system are correct and consistent with the current 2026/27 FPL data.

==================================================
1. AUTHORITATIVE PRICE SOURCE
==================================================

Identify the single authoritative source currently being used for 2026/27 FPL player prices.

Determine:

- where prices are ingested from
- how prices are stored in the database
- the database field used for price
- how prices are converted/scaled (£m vs tenths)
- how projections access price
- how the optimizer accesses price
- how positional percentiles access price
- how the frontend accesses price

There must be ONE canonical current price for every active player.

Do NOT maintain separate hard-coded price tables.

==================================================
2. FULL PLAYER-PRICE AUDIT
==================================================

Audit ALL current 2026/27 players, not just Gabriel.

For every player compare:

FPL authoritative price
vs
database price
vs
projection-engine price
vs
optimizer price
vs
positional-value diagnostic price
vs
frontend displayed price

Produce a reconciliation report:

Player | Position | FPL Price | DB Price | Projection Price | Optimizer Price | UI Price | Status

Status should be:

MATCH
MISMATCH
MISSING
STALE
INVALID

Do not silently correct mismatches.

==================================================
3. INVESTIGATE THE ROOT CAUSE
==================================================

For every mismatch category, determine WHY it occurred.

Possible causes include:

- stale database records
- historical player records being used instead of current records
- incorrect player ID mapping
- duplicate player records
- transfer/club changes
- stale cached projection snapshots
- £m vs tenths conversion
- incorrect joins
- frontend hard-coded values
- historical-season prices being reused
- ingestion not refreshing prices
- incorrect API field mapping

Do not assume Gabriel is the only affected player.

==================================================
4. CURRENT 2026/27 PRICE SNAPSHOT
==================================================

Refresh the authoritative 2026/27 player data if necessary.

Ensure every active player has:

- player ID
- current club
- position
- current price
- current FPL status

Prices must correspond to the CURRENT 2026/27 game.

Do not use historical 2025/26 prices for the active 2026/27 player pool.

==================================================
5. TRANSFER / CLUB CHANGE INTEGRITY
==================================================

Because we previously discovered issues involving transferred players, verify that player identity is preserved across club changes.

A player who transferred must NOT accidentally inherit:

- previous club's current price
- previous club's player record
- previous season's price
- stale projection price

Player identity and current club must be correctly separated from historical statistics.

==================================================
6. PRICE SCALE VALIDATION
==================================================

Verify the internal representation.

If the database stores:

£8.0m as 80
or
£8.0m as 8.0

make this explicit.

Verify that conversions are correct everywhere.

Add tests for representative prices including:

£4.0m
£4.5m
£5.0m
£5.5m
£6.0m
£6.5m
£7.0m
£8.0m
£9.5m
£12.0m
£15.5m

No floating-point or tenths conversion errors.

==================================================
7. POSITIONAL PRICE PERCENTILES
==================================================

Once the canonical prices are verified, recalculate:

pos_price_percentile
pos_xp_percentile
pos_value_percentile

Price percentile MUST be calculated against current players in the SAME position.

Examples:

Gabriel £8.0m → percentile among DEF
Raya £6.0m → percentile among GKP
Igor Jesus £6.0m → percentile among FWD
Haaland £15.5m → percentile among FWD

Do not hard-code expected percentile values.

Calculate them dynamically from the verified current price pool.

==================================================
8. OPTIMIZER PRICE INTEGRITY
==================================================

Verify that the optimizer uses the same canonical prices.

Test:

- total squad cost
- £100m budget constraint
- player individual prices
- remaining bank
- transfer/price updates

The optimizer must never receive a different price from the projection or frontend layer.

==================================================
9. FRONTEND PRICE INTEGRITY
==================================================

Verify every player displayed in:

- pitch
- player projections table
- diagnostics
- mode comparison
- player details
- optimizer results

uses the canonical current price.

No hard-coded player prices.

==================================================
10. REGRESSION TESTS
==================================================

Add tests ensuring:

1. All active players have a valid current price.
2. No duplicate current-player records have conflicting prices.
3. DB price matches authoritative ingestion price.
4. Projection price matches DB price.
5. Optimizer price matches DB price.
6. Positional percentile uses DB/current price.
7. Frontend/API price matches backend price.
8. £m/tenths conversion is consistent.
9. Historical prices cannot overwrite current prices.
10. Transfer/club changes cannot produce stale prices.
11. Price refresh correctly updates downstream consumers.

Create a test that fails if ANY current player has inconsistent prices between these layers.

==================================================
11. FULL RECOMPUTATION
==================================================

After the price audit is complete:

1. Refresh the canonical player data.
2. Recalculate positional price percentiles.
3. Recalculate any dependent value diagnostics.
4. Re-run projections ONLY where price is legitimately a feature/input.
5. Re-run the optimizer.
6. Verify budget calculations.

Do NOT retrain ML models unless the audit proves that price corruption entered the training dataset.

If historical training data contains price inconsistencies, identify them separately and report them rather than silently changing them.

==================================================
12. FINAL SANITY CHECK
==================================================

Explicitly verify these players:

- Gabriel = £8.0m
- Raya = £6.0m
- Igor Jesus = £6.0m
- Haaland = £15.5m

Then inspect the full price distribution by position:

GKP
DEF
MID
FWD

Report:

minimum
maximum
median
number of players
price distribution

This should make obvious whether an entire position has stale or incorrect pricing.

==================================================
13. DO NOT CHANGE THE OPTIMIZER
==================================================

Do NOT modify optimizer objectives.

Do NOT modify ML models.

Do NOT introduce artificial positional price rules.

The budget already accounts for the fact that different positions occupy different price ranges.

We only need the optimizer to receive the CORRECT current FPL prices.

==================================================
14. DOCUMENTATION
==================================================

Update the project documentation.

Document:

- authoritative price source
- price data flow
- internal representation
- reconciliation results
- root causes of mismatches
- transfer handling
- positional percentile methodology
- tests added
- final validation

Save this prompt under:

docs/prompts/FPL_PRICE_DATA_INTEGRITY_AUDIT.md

Remember:

EVERY DEVELOPMENT PHASE MUST UPDATE THE DOCUMENTATION.

==================================================
15. FINAL REPORT
==================================================

Return:

1. Number of players audited.
2. Number of matching prices.
3. Number of mismatches.
4. Number of stale records.
5. Number of missing prices.
6. Root causes discovered.
7. Corrected data flow.
8. Full reconciliation summary.
9. Gabriel verification.
10. Raya verification.
11. Igor Jesus verification.
12. Haaland verification.
13. Positional price distribution.
14. Optimizer budget verification.
15. Tests passed.
16. Documentation updated.

Do NOT begin Phase 3C.

STOP after the audit and correction.

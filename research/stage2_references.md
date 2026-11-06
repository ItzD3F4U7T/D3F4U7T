# Stage 2 Reading List

1. Cont, Kukanov & Stoikov, “The Price Impact of Order Book Events,” Journal of Financial Econometrics (2014). https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1712822
2. Kolm, Turiel & Westray, “Deep Order Flow Imbalance: Extracting Alpha at Multiple Horizons from the Limit Order Book,” Mathematical Finance (2023). https://doi.org/10.1111/mafi.12413
3. “Deep limit order book forecasting: a microstructural guide” (2025). https://pmc.ncbi.nlm.nih.gov/articles/PMC12315853/
4. Tripathi, Dixit & Vipul, “Information content of order imbalance in an order-driven market: Indian Evidence,” Finance Research Letters (2021). https://www.sciencedirect.com/science/article/pii/S1544612320316779
5. “Major Issues in High-Frequency Financial Data Analysis: A Survey of Solutions” (2025). https://www.mdpi.com/2227-7390/13/3/347

## How these sources informed Stage 2

- Cont, Kukanov & Stoikov motivate the order-book event categories and the distinction between limit-order additions, cancellations and trades; Stage 2 uses a simplified best-quote snapshot, not their full OFI estimator.
- Kolm, Turiel & Westray motivate stationary order-flow-derived features and evaluation across multiple horizons; this project does not train a predictor or claim alpha.
- The microstructural guide provides foundational definitions for book sides, price levels, quantities and event types.
- The Indian Evidence paper motivates treating order imbalance as a market-microstructure variable whose relevance must be evaluated by venue and horizon, not assumed universal.
- The high-frequency-data survey motivates careful handling of event timestamps, message data and data-quality issues; Stage 2 currently uses sequence numbers rather than exchange timestamps.

No external GitHub implementation was copied. The implementation in this repository is original project code; the references above are used for concepts and experimental framing.

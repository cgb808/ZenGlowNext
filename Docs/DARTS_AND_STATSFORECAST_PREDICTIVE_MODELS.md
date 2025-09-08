## Darts (Unit8)

**License:** Apache 2.0

**Why?**

A unified library for time-series forecasting, supporting deep learning models (e.g., N-BEATS, TFT, N-HiTS) and classical methods (e.g., ARIMA, Exponential Smoothing).
Includes pre-trained models and supports custom training.

**Models:**

*   N-BEATS (Neural Basis Expansion Analysis for Time Series)
*   TFT (Temporal Fusion Transformer)
*   N-HiTS (Neural Hierarchical Interpolation for Time Series)

**Example:**
```python
from darts.models import NBEATSModel
from darts.datasets import AirPassengersDataset

series = AirPassengersDataset().load()
model = NBEATSModel(input_chunk_length=24, output_chunk_length=12)
model.fit(series)
forecast = model.predict(n=12)
```

**Pros:**

*   Easy to use, modular, and supports PyTorch.
*   Works well for both univariate and multivariate time series.


**Cons:**

*   Requires some tuning for optimal performance.




## 2. StatsForecast (Nixtla)

**License:** Apache 2.0

**Why?**

Open-source library from Nixtla, the creators of TimeGPT.
Includes lightweight statistical and ML models (e.g., AutoARIMA, ETS, and ML-based models like AutoTheta).

**Example:**
```python
from statsforecast import StatsForecast
from statsforecast.models import AutoARIMA

sf = StatsForecast(models=[AutoARIMA()], freq='H')
forecasts = sf.forecast(df=your_data, h=24)
```

**Pros:**

*   Fast and scalable for large datasets.
*   Supports GPU acceleration.


**Cons:**

*   Less "foundation model" power than TimeGPT, but highly efficient.

## NeuralProphet (Meta)

**License:** MIT

**Why?**

Inspired by Prophet but adds neural network components for improved accuracy.

**Example:**
```python
from neuralprophet import NeuralProphet

model = NeuralProphet()
model.fit(your_data, freq='H')
future = model.make_future_dataframe(your_data, periods=24)
forecast = model.predict(future)
```

**Pros:**

*   Combines simplicity with neural network power.


**Cons:**

*   Slower than Prophet for large datasets.

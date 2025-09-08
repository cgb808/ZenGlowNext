# API Documentation

Audience: Front-end Developers (iOS/Android).

Purpose: A practical guide on how to interact with the cloud API, including endpoint definitions, request/response formats, and examples.

## 1. Introduction

Welcome to the Wellness Prediction API documentation. This guide will help you integrate your mobile applications with our cloud backend to send wellness data and receive forecasts, insights, and real-time alerts.

- Base URL: https://api.yourdomain.com

## 2. Authentication

All API requests must include an authentication token.

- Header: `Authorization: Bearer <YOUR_JWT_TOKEN>`

## 3. Endpoints

### A. Ingest Wellness Data

This endpoint is used to send data from the child's mobile application to the cloud. It should be called periodically (e.g., every 15-30 minutes).

- URL: `/api/ingest`
- Method: POST
- Request Body (application/json):

```json
{
  "child_id": "child_123",
  "timestamp": 1691928000,
  "wellness_metrics": {
    "hr": 75.0,
    "stress": 0.65,
    "activity": 0.8,
    "sleep_duration": 28800,
    "sleep_state": "deep"
  },
  "interaction": {
    "event": "positive_feedback",
    "activity": "reading_game"
  },
  "context": {
    "ambient_light": 500,
    "noise_level": 60,
    "user_profile": {
      "age": 8,
      "baseline_stress": 0.2
    },
    "school_events": [{ "event": "math_test", "time": "2025-08-15T09:00:00" }]
  }
}
```

Success Response (201 Created):

```json
{ "status": "success" }
```

Error Responses:

- 400 Bad Request: Missing required fields in the request body.
- 401 Unauthorized: Invalid or missing authentication token.
- 500 Internal Server Error: A server-side error occurred.

### B. Get Wellness Forecast

Retrieve a multi-variate forecast for the next 24 hours.

- URL: `/api/forecast/<child_id>`
- Method: GET
- URL Parameters:
  - `child_id` (string, required): The ID of the child.

Success Response (200 OK):

```json
{
  "forecast": {
    "timestamp": ["2025-08-13T05:00:00", "2025-08-13T06:00:00", "..."],
    "stress": [0.66, 0.68, "..."],
    "sleep_duration": [7.1, 7.0, "..."]
  }
}
```

Error Responses:

- 404 Not Found: No data exists for the specified child_id.

### C. Generate Actionable Insights

Request a natural language recommendation based on the latest forecast and historical context.

- URL: `/api/insights`
- Method: POST
- Request Body (application/json):

```json
{ "child_id": "child_123" }
```

Success Response (200 OK):

```json
{
  "recommendation": "Your child’s stress is predicted to rise ahead of the math test. To mitigate this, consider starting the bedtime routine 30 minutes earlier tonight."
}
```

## 4. Real-Time Alerts (WebSockets)

The parent app can subscribe to a WebSocket to receive real-time alerts and updates for the (enhanced)ZenMoonAvitar.

- URL: `wss://api.yourdomain.com/api/alerts`
- Connection: Use a standard WebSocket client library (e.g., Socket.IO for JavaScript).

Events to Emit (Client → Server):

- `subscribe`: Call this immediately after connecting to join a child's specific alert room.

```javascript
socket.emit('subscribe', { child_id: 'child_123' });
```

Events to Listen For (Server → Client):

- `alert`: Fired when a significant event or proactive tip is generated.

Payload:

```json
{
  "child_id": "child_123",
  "message": "High stress detected. Consider a calming activity.",
  "type": "proactive_tip"
}
```

- `avatar_update`: Provides real-time state changes for the ZenMoonAvitar.

Payload:

```json
{
  "child_id": "child_123",
  "state": "nervous",
  "reason": "High stress forecast before upcoming test."
}
```

#!/usr/bin/env python3
"""
ZenGlow Comprehensive Tech Curator Demo
Demonstrates enhanced curation for sensor data, mobile APIs, enterprise tools

This demo shows the comprehensive tech stack curator in action, highlighting:
- Sensor/IoT code samples (Arduino, ESP32, Bluetooth)
- Mobile/Wearable integration (health sensors, fitness tracking)
- API Gateway configurations (Kong plugins, rate limiting)
- Modern development ecosystem (GitHub tools, VS Code extensions, MCP)
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any


def create_demo_samples() -> Dict[str, Any]:
    """Create demonstration samples showing enhanced curation capabilities."""

    demo_samples = {
        # Sensor/IoT samples
        "sensor_samples": [
            {
                "content": """
// ESP32 Bluetooth Heart Rate Sensor
#include "BluetoothSerial.h"
#include "esp_bt.h"

BluetoothSerial SerialBT;

void setup() {
    Serial.begin(115200);
    SerialBT.begin("ESP32-HeartRate");
    Serial.println("The device started, now you can pair it with bluetooth!");
}

void loop() {
    int heartRate = readHeartRateSensor();
    SerialBT.printf("HR:%d\\n", heartRate);
    delay(1000);
}

int readHeartRateSensor() {
    // Simulate heart rate reading from sensor
    return random(60, 100);
}
                """,
                "path": "src/sensors/heart_rate_bluetooth.cpp",
                "repository_name": "espressif/esp32-health-monitor",
                "licenses": ["MIT"],
                "size": 520,
                "alphanum_fraction": 0.7,
                "avg_line_length": 35,
                "max_line_length": 80,
                "quality": 0.8,
            },
            {
                "content": """
import asyncio
import bluetooth
from typing import Dict, Optional
from fastapi import WebSocket

class BluetoothSensorManager:
    def __init__(self):
        self.connected_devices = {}
        self.sensor_data = {}
    
    async def scan_for_sensors(self) -> Dict[str, str]:
        \"\"\"Scan for nearby Bluetooth LE health sensors\"\"\"
        devices = bluetooth.discover_devices(lookup_names=True)
        health_devices = {}
        
        for addr, name in devices:
            if any(keyword in name.lower() for keyword in 
                   ['heart', 'fitness', 'health', 'sensor']):
                health_devices[addr] = name
        
        return health_devices
    
    async def stream_sensor_data(self, websocket: WebSocket):
        \"\"\"Stream real-time sensor data via WebSocket\"\"\"
        while True:
            for device_id, data in self.sensor_data.items():
                await websocket.send_json({
                    "device_id": device_id,
                    "timestamp": data["timestamp"],
                    "heart_rate": data.get("heart_rate"),
                    "steps": data.get("steps"),
                    "temperature": data.get("temperature")
                })
            await asyncio.sleep(1)
                """,
                "path": "app/sensors/bluetooth_manager.py",
                "repository_name": "zenglow/sensor-api",
                "licenses": ["Apache-2.0"],
                "size": 1240,
                "alphanum_fraction": 0.65,
                "avg_line_length": 42,
                "max_line_length": 85,
                "quality": 0.75,
            },
        ],
        # API Gateway samples
        "api_gateway_samples": [
            {
                "content": """
-- Kong Rate Limiting Plugin for Sensor APIs
local kong = kong
local ngx = ngx

local SensorRateLimitHandler = {}

SensorRateLimitHandler.PRIORITY = 1000
SensorRateLimitHandler.VERSION = "1.0.0"

function SensorRateLimitHandler:access(conf)
    local identifier = kong.client.get_ip()
    local sensor_type = kong.request.get_header("X-Sensor-Type")
    
    -- Different rate limits for different sensor types
    local limit = conf.default_limit
    if sensor_type == "heart-rate" then
        limit = conf.heart_rate_limit or 1000  -- High frequency for heart rate
    elseif sensor_type == "gps" then
        limit = conf.gps_limit or 100  -- Lower for GPS
    end
    
    -- Check rate limit
    local current_usage = kong.cache:get("rate_limit:" .. identifier) or 0
    if current_usage >= limit then
        return kong.response.exit(429, {
            message = "Rate limit exceeded for sensor type: " .. (sensor_type or "unknown")
        })
    end
    
    -- Increment counter
    kong.cache:set("rate_limit:" .. identifier, current_usage + 1, 60)
end

return SensorRateLimitHandler
                """,
                "path": "kong/plugins/sensor-rate-limit/handler.lua",
                "repository_name": "kong/kong-plugin-sensor-rate-limit",
                "licenses": ["Apache-2.0"],
                "size": 980,
                "alphanum_fraction": 0.6,
                "avg_line_length": 45,
                "max_line_length": 95,
                "quality": 0.85,
            },
            {
                "content": """
# Kong API Gateway Configuration for ZenGlow Sensor Platform
version: '3.8'

services:
  kong:
    image: kong:3.4
    environment:
      KONG_DATABASE: postgres
      KONG_PG_HOST: db
      KONG_PG_DATABASE: kong
      KONG_PG_USER: kong
      KONG_PG_PASSWORD: kong
      KONG_PROXY_ACCESS_LOG: /dev/stdout
      KONG_ADMIN_ACCESS_LOG: /dev/stdout
      KONG_PROXY_ERROR_LOG: /dev/stderr
      KONG_ADMIN_ERROR_LOG: /dev/stderr
      KONG_ADMIN_LISTEN: 0.0.0.0:8001
      KONG_PLUGINS: bundled,sensor-rate-limit,health-check
    ports:
      - "8000:8000"
      - "8443:8443"
      - "8001:8001"
      - "8444:8444"
    depends_on:
      - db
    volumes:
      - ./kong/plugins:/usr/local/share/lua/5.1/kong/plugins
    networks:
      - sensor-network

  sensor-api:
    build: ./sensor-api
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/sensors
      - REDIS_URL=redis://redis:6379
    ports:
      - "8080:8080"
    depends_on:
      - db
      - redis
    networks:
      - sensor-network

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: kong
      POSTGRES_USER: kong
      POSTGRES_PASSWORD: kong
    volumes:
      - kong_data:/var/lib/postgresql/data
    networks:
      - sensor-network

networks:
  sensor-network:
    driver: bridge

volumes:
  kong_data:
                """,
                "path": "docker-compose.kong.yml",
                "repository_name": "zenglow/api-gateway-setup",
                "licenses": ["MIT"],
                "size": 1450,
                "alphanum_fraction": 0.55,
                "avg_line_length": 38,
                "max_line_length": 75,
                "quality": 0.7,
            },
        ],
        # Development ecosystem samples
        "dev_ecosystem_samples": [
            {
                "content": """
{
  "name": "zenglow-sensor-extension",
  "displayName": "ZenGlow Sensor Tools",
  "description": "VS Code extension for sensor data visualization and debugging",
  "version": "1.0.0",
  "engines": {
    "vscode": "^1.85.0"
  },
  "categories": ["Other"],
  "activationEvents": [
    "onCommand:zenglow.connectSensor",
    "onView:sensorData"
  ],
  "main": "./out/extension.js",
  "contributes": {
    "commands": [
      {
        "command": "zenglow.connectSensor",
        "title": "Connect Bluetooth Sensor",
        "category": "ZenGlow"
      },
      {
        "command": "zenglow.visualizeSensorData",
        "title": "Visualize Sensor Data",
        "category": "ZenGlow"
      }
    ],
    "views": {
      "explorer": [
        {
          "id": "sensorData",
          "name": "Sensor Data",
          "when": "zenglow.sensorConnected"
        }
      ]
    },
    "configuration": {
      "title": "ZenGlow Sensor Tools",
      "properties": {
        "zenglow.autoConnect": {
          "type": "boolean",
          "default": true,
          "description": "Automatically connect to known sensors"
        },
        "zenglow.dataRetention": {
          "type": "number",
          "default": 3600,
          "description": "Data retention period in seconds"
        }
      }
    }
  },
  "scripts": {
    "compile": "tsc -p ./",
    "watch": "tsc -watch -p ./"
  },
  "devDependencies": {
    "@types/vscode": "^1.85.0",
    "@types/node": "^18.x",
    "typescript": "^5.0.0"
  }
}
                """,
                "path": "extensions/zenglow-sensor-tools/package.json",
                "repository_name": "microsoft/vscode-zenglow-sensors",
                "licenses": ["MIT"],
                "size": 1680,
                "alphanum_fraction": 0.6,
                "avg_line_length": 25,
                "max_line_length": 65,
                "quality": 0.8,
            },
            {
                "content": """
/**
 * ZenGlow MCP (Model Context Protocol) Server for Sensor Data
 * Provides AI assistants with real-time sensor data context
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';

const SensorDataSchema = z.object({
  device_id: z.string(),
  sensor_type: z.enum(['heart_rate', 'temperature', 'accelerometer', 'gps']),
  timestamp: z.string(),
  value: z.number(),
  unit: z.string()
});

class ZenGlowSensorMCPServer {
  private server: Server;
  private sensorData: Map<string, any[]> = new Map();

  constructor() {
    this.server = new Server(
      {
        name: 'zenglow-sensor-mcp',
        version: '1.0.0',
        description: 'MCP server for ZenGlow sensor data integration'
      },
      {
        capabilities: {
          resources: {},
          tools: {}
        }
      }
    );

    this.setupTools();
    this.setupResources();
  }

  private setupTools() {
    // Tool for getting current sensor readings
    this.server.setRequestHandler('tools/call', async (request) => {
      const { name, arguments: args } = request.params;

      if (name === 'get_sensor_data') {
        const { device_id, sensor_type, last_n } = args as {
          device_id?: string;
          sensor_type?: string;
          last_n?: number;
        };

        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(await this.getSensorData(device_id, sensor_type, last_n))
            }
          ]
        };
      }

      if (name === 'analyze_sensor_patterns') {
        const { device_id, time_range } = args as {
          device_id: string;
          time_range: string;
        };

        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(await this.analyzeSensorPatterns(device_id, time_range))
            }
          ]
        };
      }

      throw new Error(`Unknown tool: ${name}`);
    });
  }

  private async getSensorData(deviceId?: string, sensorType?: string, lastN: number = 10) {
    // Implementation for retrieving sensor data
    return {
      devices: Array.from(this.sensorData.keys()),
      latest_readings: this.getLatestReadings(deviceId, sensorType, lastN)
    };
  }

  private async analyzeSensorPatterns(deviceId: string, timeRange: string) {
    // Implementation for analyzing sensor patterns
    return {
      device_id: deviceId,
      analysis: 'Pattern analysis results',
      trends: ['increasing', 'stable', 'decreasing'],
      anomalies: []
    };
  }

  async start() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.log('ZenGlow Sensor MCP Server running');
  }
}

// Start server
const server = new ZenGlowSensorMCPServer();
server.start().catch(console.error);
                """,
                "path": "mcp-servers/zenglow-sensor/src/index.ts",
                "repository_name": "zenglow/mcp-sensor-server",
                "licenses": ["MIT"],
                "size": 2890,
                "alphanum_fraction": 0.68,
                "avg_line_length": 40,
                "max_line_length": 95,
                "quality": 0.85,
            },
        ],
    }

    return demo_samples


def demonstrate_quality_scoring():
    """Demonstrate the enhanced quality scoring for different sample types."""

    print("🔍 ZenGlow Comprehensive Tech Curator - Quality Scoring Demo")
    print("=" * 70)

    # Load config
    config_path = Path("data_sources/professional_reference/zenglow_tech_config.yaml")
    if config_path.exists():
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
    else:
        print("⚠️  Configuration file not found, using demo config")
        config = {
            "tech_stack": {
                "c++": {
                    "priority": "high",
                    "weight_modifier": 1.2,
                    "quality_boost": 0.2,
                },
                "python": {
                    "priority": "critical",
                    "weight_modifier": 1.4,
                    "quality_boost": 0.2,
                },
                "lua": {
                    "priority": "medium",
                    "weight_modifier": 1.3,
                    "quality_boost": 0.2,
                },
                "typescript": {
                    "priority": "critical",
                    "weight_modifier": 1.5,
                    "quality_boost": 0.3,
                },
                "json": {
                    "priority": "medium",
                    "weight_modifier": 1.0,
                    "quality_boost": 0.1,
                },
            }
        }

    demo_samples = create_demo_samples()

    # Simulate quality scoring function
    def mock_calculate_quality_score(sample, language, config):
        base_score = sample.get("quality", 0.0)

        # Apply tech-specific bonuses
        bonuses = 0.0
        content = sample.get("content", "").lower()
        path = sample.get("path", "").lower()
        repo = sample.get("repository_name", "").lower()

        # Sensor/IoT bonus
        sensor_keywords = ["sensor", "bluetooth", "esp32", "heart-rate", "arduino"]
        if any(kw in content or kw in path or kw in repo for kw in sensor_keywords):
            bonuses += 0.25

        # API gateway bonus
        gateway_keywords = ["kong", "rate-limit", "api-gateway", "proxy"]
        if any(kw in content or kw in path or kw in repo for kw in gateway_keywords):
            bonuses += 0.2

        # Dev ecosystem bonus
        dev_keywords = ["vscode", "extension", "mcp", "github"]
        if any(kw in content or kw in path or kw in repo for kw in dev_keywords):
            bonuses += 0.15

        return min(1.0, base_score + bonuses)

    # Demonstrate scoring for each category
    categories = [
        ("Sensor/IoT Samples", "sensor_samples", ["c++", "python"]),
        ("API Gateway Samples", "api_gateway_samples", ["lua", "yaml"]),
        ("Dev Ecosystem Samples", "dev_ecosystem_samples", ["json", "typescript"]),
    ]

    for category_name, category_key, languages in categories:
        print(f"\n📊 {category_name}")
        print("-" * 50)

        for i, sample in enumerate(demo_samples[category_key]):
            language = languages[i % len(languages)]
            quality_score = mock_calculate_quality_score(sample, language, config)

            print(f"\nSample {i+1}: {sample['path']}")
            print(f"  Language: {language}")
            print(f"  Repository: {sample['repository_name']}")
            print(f"  Base Quality: {sample['quality']:.2f}")
            print(f"  Enhanced Score: {quality_score:.2f}")
            print(f"  Size: {sample['size']} bytes")
            print(f"  Avg Line Length: {sample['avg_line_length']}")

            # Identify what makes this sample valuable
            content = sample.get("content", "").lower()
            path = sample.get("path", "").lower()
            repo = sample.get("repository_name", "").lower()

            bonuses = []
            if any(
                kw in content or kw in path or kw in repo
                for kw in ["sensor", "bluetooth", "esp32", "heart-rate", "arduino"]
            ):
                bonuses.append("Sensor/IoT tech")

            if any(
                kw in content or kw in path or kw in repo
                for kw in ["kong", "rate-limit", "api-gateway", "proxy"]
            ):
                bonuses.append("API Gateway")

            if any(
                kw in content or kw in path or kw in repo
                for kw in ["vscode", "extension", "mcp", "github"]
            ):
                bonuses.append("Dev Ecosystem")

            if bonuses:
                print(f"  🎯 Bonuses: {', '.join(bonuses)}")

    print(f"\n✨ Quality Scoring Summary")
    print("=" * 50)
    print("The enhanced curator now provides specialized scoring for:")
    print("• 🔌 Sensor/IoT: Arduino, ESP32, Bluetooth, health sensors (+25% bonus)")
    print("• 🚪 API Gateway: Kong plugins, rate limiting, proxies (+20% bonus)")
    print(
        "• 🛠️  Dev Ecosystem: VS Code extensions, MCP servers, GitHub tools (+15% bonus)"
    )
    print("• 📱 Mobile/Wearable: Health APIs, fitness tracking, device integration")
    print("• 🏢 Enterprise: Microservices, Kubernetes, monitoring, observability")
    print("\nThis enables precise curation of professional-grade code samples")
    print("tailored to ZenGlow's comprehensive technology requirements!")


def show_config_overview():
    """Show overview of the comprehensive configuration."""

    print("\n🗂️  ZenGlow Comprehensive Tech Stack Configuration")
    print("=" * 60)

    config_path = Path("data_sources/professional_reference/zenglow_tech_config.yaml")
    if not config_path.exists():
        print("⚠️  Configuration file not found")
        return

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    tech_stack = config.get("tech_stack", {})

    # Group by priority
    priorities = {}
    for lang, conf in tech_stack.items():
        priority = conf.get("priority", "medium")
        if priority not in priorities:
            priorities[priority] = []
        priorities[priority].append((lang, conf))

    for priority in ["critical", "high", "medium"]:
        if priority in priorities:
            print(f"\n{priority.upper()} Priority Technologies:")
            print("-" * 30)

            for lang, conf in priorities[priority]:
                max_samples = conf.get("max_samples", 1000)
                weight = conf.get("weight_modifier", 1.0)
                keywords = conf.get("keywords", [])[:5]  # Show first 5 keywords

                print(f"  📦 {lang}")
                print(f"     Max samples: {max_samples}")
                print(f"     Weight: {weight}x")
                print(f"     Keywords: {', '.join(keywords)}...")

    # Show keyword categories
    zenglow_keywords = config.get("zenglow_keywords", {})
    print(f"\n🔍 Specialized Keyword Categories:")
    print("-" * 35)

    for category, keywords in zenglow_keywords.items():
        if isinstance(keywords, list):
            print(f"  {category}: {len(keywords)} keywords")
            print(f"    Example: {', '.join(keywords[:3])}...")

    print(f"\n✅ Configuration loaded successfully!")
    print(f"   Total languages: {len(tech_stack)}")
    print(f"   Keyword categories: {len(zenglow_keywords)}")


if __name__ == "__main__":
    print("🚀 ZenGlow Comprehensive Tech Curator Demo")
    print("=" * 50)
    print("Enhanced for sensor data, mobile APIs, enterprise tools, and dev ecosystem")

    show_config_overview()
    demonstrate_quality_scoring()

    print(f"\n🎯 Next Steps:")
    print("1. Install dependencies: pip install datasets PyYAML")
    print(
        "2. Run curator: python scripts/zenglow_comprehensive_curator.py --priority-only"
    )
    print("3. Check curated samples in: data_sources/professional_reference/curated/")
    print("\nThis will curate high-quality code samples for all ZenGlow technologies!")

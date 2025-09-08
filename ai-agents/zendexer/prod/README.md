# 📚 ZenDexer Production Parental Predictor - Documentation Index

## 🎯 Quick Navigation

| Document                                                           | Purpose                                   | Audience               |
| ------------------------------------------------------------------ | ----------------------------------------- | ---------------------- |
| **[README_PARENTAL_PREDICTOR.md](./README_PARENTAL_PREDICTOR.md)** | Complete overview and user guide          | All stakeholders       |
| **[TECHNICAL_ARCHITECTURE.md](./TECHNICAL_ARCHITECTURE.md)**       | Deep technical details and architecture   | Developers, Architects |
| **[OPERATIONS_RUNBOOK.md](./OPERATIONS_RUNBOOK.md)**               | Day-to-day operations and troubleshooting | DevOps, SRE Teams      |

---

## 🔍 Documentation Overview

### 📖 [Main Documentation](./README_PARENTAL_PREDICTOR.md)

**Target Audience**: Product managers, developers, and family users

- **Overview**: Complete service description and capabilities
- **Features**: Parental dashboard and child wellness tracking
- **Configuration**: Environment setup and deployment
- **API Reference**: Endpoint documentation
- **Privacy & Compliance**: Security and legal considerations

### 🏗️ [Technical Architecture](./TECHNICAL_ARCHITECTURE.md)

**Target Audience**: Software architects and senior developers

- **System Architecture**: Service interactions and data flow
- **Performance Optimization**: Scaling and tuning strategies
- **Security Implementation**: Encryption and access control
- **Monitoring & Observability**: Metrics and alerting
- **Disaster Recovery**: Backup and restoration procedures

### 🚨 [Operations Runbook](./OPERATIONS_RUNBOOK.md)

**Target Audience**: DevOps engineers and site reliability engineers

- **Quick Start**: Essential deployment commands
- **Incident Response**: Troubleshooting procedures
- **Performance Tuning**: Optimization techniques
- **Monitoring**: Health checks and alerting
- **Maintenance**: Routine and planned procedures

---

## 🚀 Getting Started Paths

### 👨‍💻 **For Developers**

1. Start with [README_PARENTAL_PREDICTOR.md](./README_PARENTAL_PREDICTOR.md) - Overview section
2. Review [TECHNICAL_ARCHITECTURE.md](./TECHNICAL_ARCHITECTURE.md) - System Architecture
3. Check [README_PARENTAL_PREDICTOR.md](./README_PARENTAL_PREDICTOR.md) - API Reference
4. Refer to [OPERATIONS_RUNBOOK.md](./OPERATIONS_RUNBOOK.md) - Quick Start

### 🛠️ **For DevOps Engineers**

1. Start with [OPERATIONS_RUNBOOK.md](./OPERATIONS_RUNBOOK.md) - Quick Start
2. Review [TECHNICAL_ARCHITECTURE.md](./TECHNICAL_ARCHITECTURE.md) - Performance Optimization
3. Check [OPERATIONS_RUNBOOK.md](./OPERATIONS_RUNBOOK.md) - Monitoring & Alerts
4. Reference [README_PARENTAL_PREDICTOR.md](./README_PARENTAL_PREDICTOR.md) - Configuration

### 🏗️ **For Architects**

1. Start with [TECHNICAL_ARCHITECTURE.md](./TECHNICAL_ARCHITECTURE.md) - Full document
2. Review [README_PARENTAL_PREDICTOR.md](./README_PARENTAL_PREDICTOR.md) - Architecture section
3. Check [OPERATIONS_RUNBOOK.md](./OPERATIONS_RUNBOOK.md) - Security Operations
4. Reference [README_PARENTAL_PREDICTOR.md](./README_PARENTAL_PREDICTOR.md) - Privacy & Compliance

### 👨‍👩‍👧‍👦 **For Product Teams**

1. Start with [README_PARENTAL_PREDICTOR.md](./README_PARENTAL_PREDICTOR.md) - Overview and Features
2. Review [README_PARENTAL_PREDICTOR.md](./README_PARENTAL_PREDICTOR.md) - Parental Dashboard Features
3. Check [README_PARENTAL_PREDICTOR.md](./README_PARENTAL_PREDICTOR.md) - Privacy & Compliance
4. Reference [TECHNICAL_ARCHITECTURE.md](./TECHNICAL_ARCHITECTURE.md) - Family-Specific Configurations

---

## 🔧 Configuration Files Reference

### Production Configuration

- **Main Compose**: `zendexer_Swarm_Prod.compose`
- **Environment**: `prod/.env` (create from samples)
- **Secrets**: Docker Swarm secrets (see Operations Runbook)

### Development Configuration

- **Dev Compose**: `../dev/zendexer_Swarm_Dev.compose`
- **Local Environment**: `../dev/.env` (create from `.env.sample`)

---

## 📊 Quick Reference

### Service Details

- **Port**: 8002
- **Model**: Microsoft Phi-2 (2.7B parameters)
- **Task Focus**: Parental prediction and family wellness
- **Privacy Mode**: Local-only processing
- **Security**: Encrypted networks, RBAC, audit logging

### Key Endpoints

- **Health**: `GET /health`
- **Predictions**: `POST /predict/child-wellness`
- **Analytics**: `GET /analytics/family/{family_id}`
- **Admin**: `POST /admin/*` (authenticated)

### Resource Requirements

- **CPU**: 2 cores (production), 3 cores (your dev setup)
- **Memory**: 3GB (production), 6GB (your dev setup)
- **Storage**: 10GB for model cache and logs
- **Network**: Secure overlay with encryption

---

## 🆘 Emergency Contacts

### Critical Issues (24/7)

- **Phone**: +1-800-ZENGLOW
- **Email**: emergency@zenglow.ai
- **Slack**: #zendexer-critical

### Business Hours Support

- **DevOps Team**: ops-team@zenglow.ai
- **Development Team**: dev-team@zenglow.ai
- **Architecture Team**: arch-team@zenglow.ai

---

## 📈 Status & Updates

- **Last Updated**: August 11, 2025
- **Documentation Version**: 1.0.0
- **Service Version**: 4.0-prod
- **Next Review**: September 11, 2025

---

## 🔗 Related Documentation

### ZenGlow Ecosystem

- **Main ZenGlow App**: `../../README.md`
- **Supabase Integration**: `../../../supabase/README.md`
- **Audio Processing**: `../../../audio-drop/README.md`

### ZenDexer AI Agents

- **Mistral Interface**: `../mistral/README.md` (if exists)
- **Phi-2 Assistant**: `../phi2-assistant/README.md` (if exists)
- **Vector Store**: `../vector-store/README.md` (if exists)

### Development Tools

- **Development Guide**: `../dev/README.md` (if exists)
- **Testing Guide**: `../../../__tests__/README.md` (if exists)
- **Deployment Guide**: `../../../scripts/README.md` (if exists)

---

**💡 Tip**: Use Ctrl+F to search within documents for specific topics or commands.

**📝 Contributing**: See `CONTRIBUTING.md` for documentation update procedures.

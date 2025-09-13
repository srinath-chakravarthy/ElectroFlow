# Claude Code Assistant Guide - Electrochemical Analysis Platform

**Version:** Production Ready | **Updated:** September 12, 2025

## System Overview
- **Universal Data Processing**: Multi-instrument files (VersaStudio + BioLogic) to 47-column standardized format
- **Registry Analysis System**: Auto-scaling platform with developer tooling and expert intelligence algorithms
- **Mixed-Mode Support**: CC-CV analysis with pure technique segmentation (119 segments from 25 original)
- **Multi-Interface Access**: Panel web app, CLI, Python API, Jupyter notebooks

## Current Status - Production Ready ✅
- **BioLogic Parser**: Complete mixed-mode segmentation + mode-aware current mapping, user validated
- **VersaStudio Parser**: Production validated with proper universal schema column selection
- **Universal Schema**: v2.1.0 with 47 columns including electrode-specific impedance measurements
- **Database**: SQLite with cross-file experiment tracking and automated migrations
- **Scale Tested**: 30K+ segments validated, performance optimized for moderate datasets

## Architecture Quick Reference
→ **[System Overview](docs/SYSTEM_OVERVIEW.md)** - Complete architecture, data flow, components  
→ **[API Reference](docs/API_REFERENCE.md)** - Backend API, registry system, usage patterns  
→ **[Development Guide](docs/DEVELOPMENT_GUIDE.md)** - Contributing, testing, code standards  
→ **[Parser Architecture](docs/PARSER_ARCHITECTURE.md)** - Universal schema, BioLogic/VersaStudio details

## Key Development Context
- **Branch**: feature/test-isolation-config (ready for clean merge to dev)
- **Parser Architecture**: Clean MPRReader (binary) + BiologicParser (integration) + universal schema mapping
- **Recent Achievement**: BioLogic reverse engineering complete with technique-aware universal schema mapping
- **Next Priority**: Production deployment with clean branch structure

## Documentation Navigation
- **Quick Start**: [README.md](README.md) - Installation and basic usage
- **Complete Docs**: [docs/](docs/) - Structured technical documentation
- **Development History**: [docs/development/](docs/development/) - Detailed implementation logs

---
**The system provides complete electrochemical data processing with registry-driven analysis, auto-discovery capabilities, and cross-file experiment tracking. BioLogic parser supports advanced CC-CV mixed-control analysis with pure technique segments.**
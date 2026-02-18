# MEMORY.md - Neo's Long-Term Memory

## Project: OpenClaw Workspace Management

### Discord Integration
- **Guild ID**: `1471828091339931867`
- **Channel Mappings**:
  - `1473309431705112688`: 🤖ai知識-openclaw (OpenClaw Deep Dive/Knowledge)
  - `1473309444539682867`: ⛓️ai知識-virtual-protocol (Virtual Protocol Knowledge)
  - `1473309457114071184`: 📰aiニュース要約 (Daily AI News)
  - `1473309473484312841`: 📋ai今日のタスクと提案 (Morning Task Report)
  - `1473308823572844605`: 💡ai活用テクニック集 (AI Tips & Techniques)
- **Lessons Learned**:
  - **Spam Filtering**: Bulk channel creation/renaming followed by multiple long-form posts can trigger Discord's automated spam protection, causing "Shadow Blocks" where API calls return OK but messages don't appear. Cooling down for several hours is the primary mitigation.
  - **Language Preference**: The user (Yusuke) prefers all outputs and system reports in Japanese.

### Infrastructure & Sync
- **GitHub Integration**:
  - Repository: `7272yusuke-design/openclaw`
  - Branch: `master` (Default, unified from main)
  - Auth: Personal Access Token (PAT)
- **Deployment**: Running in VPS/Docker/Ubuntu environment. Security focuses on SSH key auth, UFW firewall, and container isolation.

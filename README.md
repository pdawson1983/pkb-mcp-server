# PKB MCP Server

A Python MCP (Model Context Protocol) server that provides a Personal Knowledge Base backed by a GitHub repository. TIL entries, prompts, and patterns are stored as Markdown files and managed through a set of tools exposed via the MCP protocol.

## Tools

The server exposes 5 tools:

| Tool | Description |
|------|-------------|
| **add_til** | Create a "Today I Learned" entry with a title, content, and tags. |
| **add_prompt** | Save a reusable prompt in a category (coding, infrastructure, documentation, general). |
| **add_pattern** | Document a reusable pattern in a category (agent, cloud, devops). |
| **search_pkb** | Search the entire knowledge base by keyword. |
| **list_entries** | Browse entries in a section (til, prompts, patterns, or all). |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GITHUB_TOKEN` | Yes | A GitHub personal access token with **Contents: Read and write** permissions on the target repository. |
| `GITHUB_REPO` | No | The GitHub repository in `owner/repo` format. Defaults to `pdawson1983/dawson-pkb`. |

## GitHub Token Setup

1. Go to [GitHub Settings > Developer settings > Fine-grained tokens](https://github.com/settings/tokens?type=beta).
2. Click **Generate new token**.
3. Give the token a descriptive name (e.g. `pkb-mcp-server`).
4. Under **Repository access**, select the repository you want to use as your knowledge base.
5. Under **Permissions > Repository permissions**, set **Contents** to **Read and write**.
6. Click **Generate token** and copy the value.

## Docker

### Build

```bash
docker build -t pkb-mcp-server .
```

### Run

```bash
docker run -i --rm \
  -e GITHUB_TOKEN="your-github-token-here" \
  -e GITHUB_REPO="owner/repo" \
  pkb-mcp-server
```

## Claude Desktop Integration

Add the following to your `claude_desktop_config.json` to use this server with Claude Desktop:

```json
{
  "mcpServers": {
    "pkb": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "-e", "GITHUB_TOKEN", "pkb-mcp-server"],
      "env": {
        "GITHUB_TOKEN": "your-github-token-here"
      }
    }
  }
}
```

The `GITHUB_REPO` environment variable should be set inside the container (e.g. baked into the image or added to the `args` with an additional `-e GITHUB_REPO=owner/repo` flag).

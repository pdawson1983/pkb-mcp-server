"""
PKB MCP Server - Personal Knowledge Base exposed via Model Context Protocol.

Provides 5 tools for managing a GitHub-backed knowledge base:
  - add_til: Create "Today I Learned" entries
  - add_prompt: Save reusable prompts
  - add_pattern: Document reusable patterns
  - search_pkb: Search the repository by keyword
  - list_entries: Browse specific sections
"""

import os
from datetime import datetime, timezone

from github import Github, GithubException
from mcp.server.fastmcp import FastMCP
from slugify import slugify

# ---------------------------------------------------------------------------
# Server & GitHub initialisation
# ---------------------------------------------------------------------------

mcp = FastMCP("pkb-server")

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise EnvironmentError("GITHUB_TOKEN environment variable is required")

GITHUB_REPO = os.environ.get("GITHUB_REPO", "pdawson1983/dawson-pkb")

_gh = Github(GITHUB_TOKEN)
_repo = _gh.get_repo(GITHUB_REPO)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_PROMPT_CATEGORIES = {"coding", "infrastructure", "documentation", "general"}
VALID_PATTERN_CATEGORIES = {"agent", "cloud", "devops"}
VALID_SECTIONS = {"til", "prompts", "patterns", "all"}

SECTION_PATH_MAP = {
    "til": "til/",
    "prompts": "ai/prompts/",
    "patterns": "patterns/",
}


def _today() -> str:
    """Return today's date as YYYY-MM-DD in UTC."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _html_url_for(path: str) -> str:
    """Build a GitHub browser URL for a file path in the repo."""
    return f"https://github.com/{GITHUB_REPO}/blob/main/{path}"


def _get_file_content(path: str) -> str | None:
    """Return the decoded text content of a file, or None if it doesn't exist."""
    try:
        contents = _repo.get_contents(path, ref="main")
        return contents.decoded_content.decode("utf-8")
    except GithubException as exc:
        if exc.status == 404:
            return None
        raise


def _create_or_update_file(path: str, content: str, message: str) -> str:
    """Create or update a file in the repo and return its browser URL.

    Returns the GitHub URL of the created/updated file.
    """
    existing = None
    try:
        existing = _repo.get_contents(path, ref="main")
    except GithubException as exc:
        if exc.status != 404:
            raise

    if existing is not None:
        _repo.update_file(
            path=path,
            message=message,
            content=content,
            sha=existing.sha,
            branch="main",
        )
    else:
        _repo.create_file(
            path=path,
            message=message,
            content=content,
            branch="main",
        )

    return _html_url_for(path)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def add_til(title: str, content: str, tags: list[str]) -> str:
    """Create a 'Today I Learned' entry in the knowledge base.

    Args:
        title: Short descriptive title for the TIL entry.
        content: The markdown body of the TIL entry.
        tags: A list of tags/keywords for categorisation.

    Returns:
        Confirmation message with the GitHub URL of the new entry.
    """
    try:
        date_str = _today()
        slug = slugify(title)
        filename = f"{date_str}-{slug}.md"
        file_path = f"til/{filename}"

        tags_yaml = ", ".join(tags) if tags else ""
        frontmatter = (
            "---\n"
            f"title: \"{title}\"\n"
            f"date: {date_str}\n"
            f"tags: [{tags_yaml}]\n"
            "---\n\n"
        )
        full_content = frontmatter + content + "\n"

        url = _create_or_update_file(
            path=file_path,
            content=full_content,
            message=f"Add TIL: {title}",
        )

        # Update til/index.md with a link to the new entry
        index_path = "til/index.md"
        existing_index = _get_file_content(index_path)
        new_link = f"- [{title}]({filename}) ({date_str})\n"

        if existing_index is not None:
            updated_index = existing_index.rstrip("\n") + "\n" + new_link
        else:
            updated_index = f"# TIL Index\n\n{new_link}"

        _create_or_update_file(
            path=index_path,
            content=updated_index,
            message=f"Update TIL index: add {title}",
        )

        return f"TIL entry created: {title}\nURL: {url}"

    except GithubException as exc:
        return f"GitHub API error while adding TIL: {exc.data.get('message', str(exc))}"
    except Exception as exc:
        return f"Error adding TIL: {exc}"


@mcp.tool()
def add_prompt(name: str, category: str, content: str, description: str) -> str:
    """Save a reusable prompt to the knowledge base.

    Args:
        name: A short name for the prompt.
        category: One of: coding, infrastructure, documentation, general.
        content: The full prompt text.
        description: A brief description of the prompt's purpose.

    Returns:
        Confirmation message with the GitHub URL of the saved prompt.
    """
    try:
        category_lower = category.lower().strip()
        if category_lower not in VALID_PROMPT_CATEGORIES:
            return (
                f"Invalid category '{category}'. "
                f"Must be one of: {', '.join(sorted(VALID_PROMPT_CATEGORIES))}"
            )

        date_str = _today()
        slug = slugify(name)
        filename = f"{slug}.md"
        file_path = f"ai/prompts/{category_lower}/{filename}"

        frontmatter = (
            "---\n"
            f"name: \"{name}\"\n"
            f"category: {category_lower}\n"
            f"description: \"{description}\"\n"
            f"date: {date_str}\n"
            "---\n\n"
        )
        full_content = frontmatter + content + "\n"

        url = _create_or_update_file(
            path=file_path,
            content=full_content,
            message=f"Add prompt: {name} ({category_lower})",
        )

        return f"Prompt saved: {name} [{category_lower}]\nURL: {url}"

    except GithubException as exc:
        return f"GitHub API error while adding prompt: {exc.data.get('message', str(exc))}"
    except Exception as exc:
        return f"Error adding prompt: {exc}"


@mcp.tool()
def add_pattern(
    name: str,
    category: str,
    problem: str,
    solution: str,
    tags: list[str],
) -> str:
    """Document a reusable pattern in the knowledge base.

    Args:
        name: A short name for the pattern.
        category: One of: agent, cloud, devops.
        problem: Description of the problem the pattern solves.
        solution: Detailed solution / implementation guidance.
        tags: A list of tags/keywords for categorisation.

    Returns:
        Confirmation message with the GitHub URL of the pattern.
    """
    try:
        category_lower = category.lower().strip()
        if category_lower not in VALID_PATTERN_CATEGORIES:
            return (
                f"Invalid category '{category}'. "
                f"Must be one of: {', '.join(sorted(VALID_PATTERN_CATEGORIES))}"
            )

        date_str = _today()
        slug = slugify(name)
        filename = f"{slug}.md"
        file_path = f"patterns/{category_lower}/{filename}"

        tags_yaml = ", ".join(tags) if tags else ""
        frontmatter = (
            "---\n"
            f"name: \"{name}\"\n"
            f"category: {category_lower}\n"
            f"date: {date_str}\n"
            f"tags: [{tags_yaml}]\n"
            "---\n\n"
        )
        body = (
            f"## Problem\n\n{problem}\n\n"
            f"## Solution\n\n{solution}\n"
        )
        full_content = frontmatter + body

        url = _create_or_update_file(
            path=file_path,
            content=full_content,
            message=f"Add pattern: {name} ({category_lower})",
        )

        return f"Pattern documented: {name} [{category_lower}]\nURL: {url}"

    except GithubException as exc:
        return f"GitHub API error while adding pattern: {exc.data.get('message', str(exc))}"
    except Exception as exc:
        return f"Error adding pattern: {exc}"


@mcp.tool()
def search_pkb(query: str) -> str:
    """Search the knowledge base by keyword.

    Args:
        query: The search term to look for across repository files.

    Returns:
        Matching files with content snippets and GitHub URLs, or a message
        indicating no results were found.
    """
    try:
        search_query = f"{query} repo:{GITHUB_REPO}"
        results = _gh.search_code(search_query)

        matches: list[str] = []
        for item in results:
            # Fetch a snippet of the file content
            try:
                file_content = item.repository.get_contents(
                    item.path, ref="main"
                )
                decoded = file_content.decoded_content.decode("utf-8")
                # Show the first 200 characters as a snippet
                snippet = decoded[:200].replace("\n", " ").strip()
                if len(decoded) > 200:
                    snippet += "..."
            except Exception:
                snippet = "(unable to retrieve snippet)"

            url = _html_url_for(item.path)
            matches.append(
                f"- **{item.path}**\n  URL: {url}\n  Snippet: {snippet}"
            )

            # Cap at 20 results to keep output manageable
            if len(matches) >= 20:
                break

        if not matches:
            return f"No results found for '{query}'."

        header = f"Found {len(matches)} result(s) for '{query}':\n\n"
        return header + "\n\n".join(matches)

    except GithubException as exc:
        return f"GitHub API error while searching: {exc.data.get('message', str(exc))}"
    except Exception as exc:
        return f"Error searching PKB: {exc}"


@mcp.tool()
def list_entries(section: str) -> str:
    """List entries in a section of the knowledge base.

    Args:
        section: One of: til, prompts, patterns, or 'all' to list everything.

    Returns:
        A structured listing of files with names, paths, and modification
        dates for the requested section.
    """
    try:
        section_lower = section.lower().strip()
        if section_lower not in VALID_SECTIONS:
            return (
                f"Invalid section '{section}'. "
                f"Must be one of: {', '.join(sorted(VALID_SECTIONS))}"
            )

        if section_lower == "all":
            sections_to_list = ["til", "prompts", "patterns"]
        else:
            sections_to_list = [section_lower]

        output_parts: list[str] = []

        for sec in sections_to_list:
            repo_path = SECTION_PATH_MAP[sec]
            header = f"## {sec.title()}\n"
            entries: list[str] = []

            try:
                items = _list_files_recursive(repo_path)
            except GithubException as exc:
                if exc.status == 404:
                    output_parts.append(header + "  (no entries yet)\n")
                    continue
                raise

            if not items:
                output_parts.append(header + "  (no entries yet)\n")
                continue

            for item_path, item_name in items:
                # Fetch last commit date for the file
                mod_date = _get_last_modified(item_path)
                url = _html_url_for(item_path)
                entries.append(
                    f"- **{item_name}**\n"
                    f"  Path: {item_path}\n"
                    f"  Modified: {mod_date}\n"
                    f"  URL: {url}"
                )

            output_parts.append(header + "\n".join(entries) + "\n")

        return "\n".join(output_parts).strip()

    except GithubException as exc:
        return f"GitHub API error while listing entries: {exc.data.get('message', str(exc))}"
    except Exception as exc:
        return f"Error listing entries: {exc}"


def _list_files_recursive(path: str) -> list[tuple[str, str]]:
    """Recursively list all files under a repo path.

    Returns a list of (path, name) tuples.
    """
    results: list[tuple[str, str]] = []
    try:
        contents = _repo.get_contents(path, ref="main")
    except GithubException as exc:
        if exc.status == 404:
            return results
        raise

    # get_contents returns a list when path is a directory
    if not isinstance(contents, list):
        contents = [contents]

    for item in contents:
        if item.type == "dir":
            results.extend(_list_files_recursive(item.path))
        else:
            results.append((item.path, item.name))

    return results


def _get_last_modified(path: str) -> str:
    """Return the date of the most recent commit touching a file, or 'unknown'."""
    try:
        commits = _repo.get_commits(path=path, sha="main")
        first = commits[0]
        return first.commit.committer.date.strftime("%Y-%m-%d")
    except Exception:
        return "unknown"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")

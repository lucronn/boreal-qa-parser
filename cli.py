import os
import sys
import json
import subprocess
import requests
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.status import Status
from boreal_parser import parse_boreal_comment, parse_trusted_ci_metadata

console = Console()

ORG_NAME = "Alignerr-Code-Labeling"

def get_gh_token():
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token
    try:
        token = subprocess.check_output(["gh", "auth", "token"], text=True).strip()
        if token:
            return token
    except Exception:
        pass
    return None

def get_headers(token):
    headers = {
        "Accept": "application/vnd.github.v3+json"
    }
    if token:
        headers["Authorization"] = f"token {token}"
    return headers

def get_repositories(headers):
    # Fetch from API
    url = f"https://api.github.com/orgs/{ORG_NAME}/repos?per_page=100"
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return [repo["name"] for repo in response.json()]
    except Exception as e:
        console.print(f"[yellow]Warning: Failed to fetch repositories via API: {e}. Using fallback defaults.[/yellow]")
    
    # Fallback list of known repos
    return [
        "lbx-rl-tasks-iso-efbb2b18-gh-task-6z1wfn0kmh",
        "lbx-rl-tasks-iso-efbb2b18-gh-task-el93e0anf",
        "lbx-rl-tasks-iso-efbb2b18-gh-task-zzpop04gg",
        "lbx-rl-tasks-iso-6e21c443-gh-task-iuo3209i3",
        "lbx-rl-tasks-iso-ad47eca1-gh-task-1gnn2097w",
        "lbx-rl-tasks-iso-5b4cc4fc-gh-task-sz9810amq",
        "lbx-rl-tasks-iso-5b4cc4fc-gh-task-sz97z0arj",
        "lbx-rl-tasks-iso-efbb2b18-gh-task-u8271m0to0"
    ]

def get_pull_requests(repo_name, headers):
    url = f"https://api.github.com/repos/{ORG_NAME}/{repo_name}/pulls?state=all"
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return []
    return response.json()

def get_pr_comments(repo_name, pr_number, headers):
    url = f"https://api.github.com/repos/{ORG_NAME}/{repo_name}/issues/{pr_number}/comments?per_page=100"
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return []
    return response.json()

@click.group()
def cli():
    """Boreal QA Parser & PR Status Dashboard CLI for Alignerr repos."""
    pass

@cli.command("list")
@click.option("--repo", default=None, help="Filter by a specific repository name.")
@click.option("--state", type=click.Choice(["open", "closed", "all"]), default="all", help="Filter PRs by state.")
def list_prs(repo, state):
    """List all PRs and their status across Alignerr repositories."""
    token = get_gh_token()
    headers = get_headers(token)
    
    if not token:
        console.print("[yellow]Warning: No GitHub token found. Rate limits will be heavily restricted. Set GITHUB_TOKEN or authenticate via 'gh auth login'.[/yellow]")
        
    repos_to_check = [repo] if repo else get_repositories(headers)
    
    table = Table(title="Alignerr PR Status & Boreal Findings Dashboard")
    table.add_column("Repository", style="cyan")
    table.add_column("PR # / Title", style="white")
    table.add_column("State", style="bold")
    table.add_column("CI Decision", style="magenta")
    table.add_column("Boreal Grade", style="yellow")
    table.add_column("Findings", style="red")
    
    with console.status("[bold green]Fetching Pull Requests and Comment Logs...") as status:
        for r_name in repos_to_check:
            prs = get_pull_requests(r_name, headers)
            for pr in prs:
                if state != "all" and pr["state"] != state:
                    continue
                
                pr_num = pr["number"]
                pr_title = pr["title"]
                pr_state = pr["state"].upper()
                
                comments = get_pr_comments(r_name, pr_num, headers)
                
                # Parse Boreal/CI comments
                decision = "N/A"
                boreal_grade = "N/A"
                num_findings = 0
                
                # Check comments starting from the newest
                for c in reversed(comments):
                    body = c.get("body", "")
                    
                    # Check general CI metadata
                    if "<!-- lbx-trusted-ci-grade -->" in body or "Decision:" in body:
                        ci_meta = parse_trusted_ci_metadata(body)
                        if ci_meta["decision"] != "unknown":
                            decision = ci_meta["decision"]
                            
                    # Parse Boreal results
                    parsed_boreal = parse_boreal_comment(body)
                    if parsed_boreal["has_boreal_section"]:
                        if parsed_boreal["grader_qa_result"]:
                            boreal_grade = parsed_boreal["grader_qa_result"]["grade"].upper()
                        num_findings = len(parsed_boreal["findings"])
                        break
                
                state_style = "green" if pr_state == "OPEN" else "grey50"
                grade_style = "green" if boreal_grade == "PASS" else ("red" if boreal_grade == "FAILED" else "yellow")
                decision_style = "green" if "pass" in decision.lower() else ("red" if "fix" in decision.lower() or "fail" in decision.lower() else "yellow")
                
                table.add_row(
                    r_name.replace("lbx-rl-tasks-iso-", ""),
                    f"#{pr_num}: {pr_title[:45]}...",
                    Text(pr_state, style=state_style),
                    Text(decision, style=decision_style),
                    Text(boreal_grade, style=grade_style),
                    Text(str(num_findings) if num_findings > 0 else "0", style="red" if num_findings > 0 else "green")
                )
                
    console.print(table)

@cli.command("view")
@click.argument("repo")
@click.argument("pr_number", type=int)
def view_pr(repo, pr_number):
    """View detailed Boreal QA pre-flight findings and CI grade for a specific PR."""
    token = get_gh_token()
    headers = get_headers(token)
    
    # Clean repo name in case user omitted the prefix
    full_repo = repo
    if not repo.startswith("lbx-"):
        # Match from known repo names or dynamically
        all_repos = get_repositories(headers)
        matched = [r for r in all_repos if repo in r]
        if matched:
            full_repo = matched[0]
            
    with console.status(f"[bold green]Fetching details for {full_repo} PR #{pr_number}...") as status:
        url = f"https://api.github.com/repos/{ORG_NAME}/{full_repo}/pulls/{pr_number}"
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            console.print(f"[red]Error: Pull Request not found or API error ({response.status_code}).[/red]")
            return
        
        pr = response.json()
        comments = get_pr_comments(full_repo, pr_number, headers)
        
    console.print(Panel(
        f"[bold cyan]{pr['title']}[/bold cyan]\n"
        f"Repo: {full_repo}\n"
        f"State: {pr['state'].upper()} | Author: {pr['user']['login']} | URL: {pr['html_url']}",
        title=f"PR #{pr_number} Details"
    ))
    
    # Parse latest comments
    boreal_results = None
    ci_metadata = None
    
    for c in reversed(comments):
        body = c.get("body", "")
        if "### Boreal Results" in body or "env qa pre-flight" in body.lower():
            boreal_results = parse_boreal_comment(body)
        if "<!-- lbx-trusted-ci-grade -->" in body or "Decision:" in body:
            ci_metadata = parse_trusted_ci_metadata(body)
            
    if ci_metadata:
        decision_text = f"[bold]Decision:[/bold] {ci_metadata['decision']}\n[bold]Next action:[/bold] {ci_metadata['next_action']}"
        console.print(Panel(decision_text, title="CI Grade Summary", border_style="magenta"))
        
        if ci_metadata["required_fixes"]:
            console.print("\n[bold red]Required Fixes:[/bold red]")
            for idx, fix in enumerate(ci_metadata["required_fixes"], 1):
                console.print(f"{idx}. [bold]{fix['title']}[/bold] (Source: `{fix['source']}`)")
                if fix['problem']:
                    console.print(f"   [yellow]Problem:[/yellow] {fix['problem']}")
                if fix['suggested_fix']:
                    console.print(f"   [green]Suggested Fix:[/green] {fix['suggested_fix']}")
                    
    if boreal_results and boreal_results["has_boreal_section"]:
        if boreal_results["grader_qa_result"]:
            qa = boreal_results["grader_qa_result"]
            summary_text = (
                f"[bold]Grade:[/bold] {qa['grade'].upper()} | [bold]Score:[/bold] {qa['score']} | "
                f"[bold]Min Axis Score:[/bold] {qa['min_axis_score']} | [bold]Model:[/bold] {qa['model']}\n"
                f"[italic]{qa['summary']}[/italic]"
            )
            console.print(Panel(summary_text, title="Boreal Grader QA Result", border_style="yellow"))
            
        if boreal_results["findings"]:
            console.print("\n[bold red]Boreal Pre-flight Findings:[/bold red]")
            for idx, f in enumerate(boreal_results["findings"], 1):
                sev_color = "red" if f['severity'] == "error" else ("yellow" if f['severity'] == "warning" else "cyan")
                console.print(f"{idx}. [{sev_color}][bold]{f['severity'].upper()}[/bold][/{sev_color}] `[{f['rule']}]` [bold]{f['title']}[/bold]")
                for detail in f['details']:
                    console.print(f"   - {detail}")
        else:
            console.print("\n[green]No Boreal pre-flight findings found![/green]")
    else:
        console.print("\n[yellow]No Boreal pre-flight feedback found in comments.[/yellow]")

if __name__ == "__main__":
    cli()

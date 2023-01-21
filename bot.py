from github import Github
from openai_helpers.helpers import compare_embeddings, compare_text, embed, complete, complete_code

# TODO: should create a branch before making a PR?

class PRBot:
    def __init__(self):
        self.token = "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"

    def apply_patches(self, repo_path, patches):
        pass

    def create_pr(self, repo, submittedPR):
        # repo.create_pull(title=title, body=body, base="master", head=head)
        pass

class SubmittedPR:
    def __init__(self, issue, changes):
        # changes is a dict of {filename: (prev_content, new_content)}
        self.changes = changes
        self.issue = issue

        self.title = self.create_title(changes, issue)
        self.body = self.create_body(changes, issue)

    def create_title(self, changes, issue):
        changed_files = [f for f in changes.keys()]
        prompt = f'What is a 1-liner description for the github PR that fixes this issue? The issue title is {issue.title} and the body is {issue.body}. The fix modified these files: {changed_files}.\nTitle:'
        title = complete(prompt)
        return title

    def create_body(self, changes, issue):
        # TODO: diff the changes and use that to create a better description
        prompt = f'What is a description of the github PR that fixes this issue? The issue title is {issue.title} and the issue body is {issue.body}. The fix modified these files: {changed_files}.\nDescription:'
        prompt += 'Respond in markdown format and break down the fix into steps.'
        description = complete(prompt)
        return "Fixes {issue.url}.\n\n{description}"

if __name__ == "__main__":
    # Example of forking a repo, creating a file and making a PR
    pb = PRBot()
    g = Github(pb.token)
    user = g.get_user()

    # Upstream repo to fork
    upstream_org = 'dmvaldman'
    upstream_name = 'bootstrap'
    upstream_repo = g.get_repo(f'{upstream_org}/{upstream_name}')

    # Fork repo if doesn't exist
    if upstream_name not in [r.name for r in user.get_repos()]:
        user.create_fork(upstream_repo)

    repo = user.get_repo(upstream_name)

    # Create file
    filename = 'echo1.py'
    commit_msg = 'commit msg'
    content = 'print("hello world")'
    repo.create_file(filename, commit_msg, content, branch="main")

    # Create PR
    upstream_repo.create_pull('title', 'body', upstream_repo.default_branch, f"pierrebhat:main", True)
from github import Github
from openai_helpers.helpers import compare_embeddings, compare_text, embed, complete, complete_code
from github import Repository

# TODO: should create a branch before making a PR?

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

    def create_body(self, changes, issue):
        return 'body'

class PRBot:
    def __init__(self):
        self.token = "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"
        self.github = Github(self.token)
        self.user = self.github.get_user()

    def create_pr(self, org, name, pr: SubmittedPR):

        # Upstream repo to fork
        upstream_repo = self.github.get_repo(f'{org}/{name}')

        # Fork repo if doesn't exist
        self.fork_repo(upstream_repo)
        repo = self.user.get_repo(name)

        # Apply PR changes to files
        self.apply_changes(repo, pr.changes)
        upstream_repo.create_pull(pr.title, pr.body, upstream_repo.default_branch, f"pierrebhat:main", True)

    def fork_repo(self, repo):
        if repo.name not in [r.name for r in self.user.get_repos()]:
            self.user.create_fork(repo)

    def apply_changes(self, repo: Repository.Repository, changes):
        for file_path, content in changes.items():
            file = repo.get_contents(file_path)
            repo.update_file(file_path, f'Updated {file.name}', content, file.sha)


if __name__ == "__main__":
    # Example of forking a repo, creating a file and making a PR
    pb = PRBot()

    org = 'twbs'
    name = 'bootstrap'
    changes = {
        'js/src/button.js' : '<Button/>',
        'js/src/tab.js' : '<Tab/>'
    }

    issue = {
    }

    pr = SubmittedPR(issue, changes)
    pb.create_pr(org, name, pr)

from github import Github, ContentFile
from openai_helpers.helpers import compare_embeddings, compare_text, embed, complete, complete_code
from multiprocessing import Pool
from functools import reduce
import os

from dotenv import load_dotenv
load_dotenv()

from repo import Repo, Issue, PR

# TODO: should create a branch before making a PR?

class SubmittedPR:
    def __init__(self, issue, changes):
        # changes is a dict of {filename: (prev_content, new_content)}
        self.changes = changes
        self.issue = issue
        self.title = self.create_title(changes, issue)
        self.body = self.create_body(changes, issue)
        print(f'TITLE: {self.title}')
        print(f'BODY: {self.body}')

    def create_title(self, changes, issue):
        changed_files = [f for f in changes.keys()]
        prompt = f'What is a 1-liner description for the github PR that fixes this issue? The issue title is {issue["title"]} and the body is {issue["body"]}. The fix modified these files: {changed_files}.\nTitle:'
        title = complete(prompt)
        return title

    def create_body(self, changes, issue):
        # TODO: diff the changes and use that to create a better description
        changed_files = [f for f in changes.keys()]
        prompt = f'What is a description of the github PR that fixes this issue? The issue title is {issue["title"]} and the issue body is {issue["body"]}. The fix modified these files: {changed_files}.\nDescription:'
        prompt += 'Respond in markdown format and break down the fix into steps.'
        description = complete(prompt)
        return f'Fixes {issue["url"]}.\n\n{description}'


class PRBot:

    extensions = ('.js', '.jsx', '.py', '.md', '.json', '.html', '.css', '.yml', '.yaml', '.ts', '.tsx', '.ipynb', '.c', '.cc', '.cpp', '.go', '.h', '.hpp', '.java', '.sol', '.sh', '.txt')
    directory_blacklist = ('build', 'dist', '.github')

    def __init__(self, org, name):
        self.token = os.getenv('PIERRE_BOT_TOKEN')
        self.github = Github(self.token)
        self.user = self.github.get_user()
        self.upstream_repo = self.github.get_repo(f'{org}/{name}')
        self.fork_repo(self.upstream_repo)
        self.repo = self.user.get_repo(name)

    def create_pr(self, pr: SubmittedPR):
        self.apply_changes(self.repo, pr.changes)
        self.upstream_repo.create_pull(pr.title, pr.body, self.upstream_repo.default_branch, f"pierrebhat:main", True)

    def fork_repo(self, repo):
        if repo.name not in [r.name for r in self.user.get_repos()]:
            self.user.create_fork(repo)

    def apply_changes(self, changes):
        for file_path, content in changes.items():
            file = self.repo.get_contents(file_path)
            self.repo.update_file(file_path, f'Updated {file.name}', content, file.sha)

    def get_all_content(self):
        contents = self.repo.get_contents("")
        output = {}
        for item in contents:
            if item.type == 'dir' and not str(item.path).startswith(self.directory_blacklist):
                contents.extend(self.repo.get_contents(item.path))
            else:
                if not str(item.name).endswith(self.extensions):
                    continue
                decoded = item.decoded_content.decode('utf-8')
                output[item.path] = decoded
        return output

if __name__ == "__main__":
    # PR Bot
    repo_org = 'karpathy'
    repo_name = 'nanoGPT'
    num_hits = 5

    bot = PRBot(repo_org, repo_name)
    repo = Repo(repo_org, repo_name)

    issues_all = repo.get_issue_list()
    issue = [issue for issue in issues_all if issue.num == 50][0]

    changes = repo.get_issue_patches(issue, num_hits=num_hits)

    # Create all file changes
    changes = bot.create_changes(changes)

    pr = SubmittedPR(issue, changes)
    # bot.create_pr(org, name, pr)

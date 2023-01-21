from github import Github

# TODO: should create a branch before making a PR?

class PRBot:
    def __init__(self):
        self.token = "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"

    def apply_patches(self, repo_path, patches):
        pass

    def create_pr(self, repo, title, body, head):
        repo.create_pull(title=title, body=body, base="master", head=head)


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
    filename = 'echo6.py'
    commit_msg = 'commit msg'
    content = 'print("hello world")'
    repo.create_file(filename, commit_msg, content, branch="main")

    # Create PR
    upstream_repo.create_pull('title', 'body', upstream_repo.default_branch, f"pierrebhat:main", True)
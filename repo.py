from github import Github
import requests
from bs4 import BeautifulSoup
from git import Repo as GitRepo
from requests_html import HTMLSession
import faiss
import re
import os
import numpy as np
import json
from openai_helpers.helpers import compare_embeddings, compare_text, embed, complete, EMBED_DIMS

# TODO:
# - Separate scraper from business logic

token = "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"
github = Github(token)
session = HTMLSession()


class Repo:
    extensions = ('.js', '.jsx', '.py', '.md', '.json', '.html', '.css', '.yml', '.yaml', '.ts', '.tsx', '.ipynb', '.c', '.cc', '.cpp', '.go', '.h', '.hpp', '.java', '.sol', '.sh', '.txt')
    directory_blacklist = ('build', 'dist', '.github')
    def __init__(self, org, name, repo_dir='repos'):
        self.org = org
        self.name = name
        self.dir = repo_dir

        self.remote_path = f'{org}/{name}'
        self.local_path = f'{repo_dir}/{name}'

        self.repo = GitRepo(self.local_path)
        self.github = github.get_repo(self.remote_path)

        self.paths, self.embeds = self.get_repo_embeddings()
        self.issue_pr_map = self.get_issue_pr_map()

        self.index = faiss.IndexFlatIP(self.embeds.shape[1])
        self.index.add(self.embeds)

    def save_embeds(self, embeds, paths):
        save_path_embed = f'embeddings/{self.name}_embeds.npy'
        save_path_paths = f'embeddings/{self.name}_paths.json'

        with open(save_path_embed, 'wb') as f:
            np.save(f, np.array(embeds))

        with open(save_path_paths, 'w') as f:
            json.dump(paths, f)

    def load_embeds(self):
        save_path_embed = f'embeddings/{self.name}_embeds.npy'
        save_path_paths = f'embeddings/{self.name}_paths.json'

        with open(save_path_embed, 'rb') as f:
            embeds = np.load(f)

        with open(save_path_paths, 'r') as f:
            paths = json.load(f)

        return paths, embeds

    def get_repo_embeddings(self, batch_size=50, save=True, max_num_files=2000):
        save_path = f'embeddings/{self.name}_embeds.npy'
        if os.path.exists(save_path):
            return self.load_embeds()

        embeddings = np.empty((0, EMBED_DIMS), np.float32)
        paths = []
        num_files = 0
        batch = []

        for root, dirs, files in os.walk(self.local_path, topdown=False):
            files = [f for f in files if not f[0] == '.' and f.endswith(Repo.extensions)]
            dirs[:] = [d for d in dirs if not d[0] == '.' and d.startswith(Repo.directory_blacklist)]
            for name in files:
                filename = os.path.join(root, name)
                try:
                    with open(filename, 'r') as f:
                        code = f.read()
                except UnicodeDecodeError:
                    continue

                if code.strip() == '':
                    continue

                batch.append((filename, code))
                num_files += 1

                if (len(batch) == batch_size or num_files > max_num_files):
                    embeddings = embed([code for _, code in batch])
                    for (filename, code), embedding in zip(batch, embeddings):
                        paths.append(filename)
                        embeddings = np.append(embeddings, [embedding], axis=0)
                    batch = []

                    if num_files > max_num_files:
                        break

        # Save as npy file
        if save:
            self.save_embeds(embeddings, paths)

        return paths, embeddings

    def get_similarity(self, text):
        repo_embeddings = self.embeds
        text_embedding = embed(text)
        similarities = []
        for filename, code_embedding in repo_embeddings.items():
            similarity = compare_embeddings(text_embedding, code_embedding)
            similarities.append((similarity, filename))

        similarities.sort(key=lambda x: x[0], reverse=True)
        return similarities

    def get_issue_pr_map(self):
        issue_pr_map = {}

        response = session.get(f'https://github.com/{self.remote_path}/issues?q=is%3Aissue+is%3Aclosed')
        soup = BeautifulSoup(response.text, 'html.parser')

        # look for aria attribute with the text `linked pull request` as a substring
        pr_els = soup.select('[aria-label^="1 linked pull request"] a')
        for issue_el in pr_els:
            linked_issue_url = issue_el.attrs['href']
            match = re.search(r'\/(\d+)\/', linked_issue_url)
            if match:
                issue_num = match.group(1)
                r = requests.get(f'https://github.com/{linked_issue_url}')
                pr_num = int(r.url.split('/')[-1])
                issue_pr_map[issue_num] = pr_num

        return issue_pr_map

    def get_nearest_files(self, issue, num_hits=5):
        issue_embedding = issue.embed
        D, I = self.index.search(np.array([issue_embedding]), num_hits)
        nearest_files = [self.paths[i] for i in I[0]]
        return nearest_files

    def calc_similarity_score(self, issue, pr):
        num_hits = min(5, 3 * pr.num_changed_files)
        nearest_files = self.get_nearest_files(issue, num_hits=num_hits)

        count_hits = 0
        count_misses = 0
        for file in pr.changed_files:
            file_abs = os.path.join(f'{self.local_path}', file)
            if file_abs in nearest_files:
                count_hits += 1
            else:
                count_misses += 1

        return count_hits, count_misses

    def check_fix_issue(issue, pr):
        parent_commit = pr.parent_commit
        changed_files = pr.changed_files
        conversation = issue.body

        # checkout the parent commit in the local repo
        self.repo.git.checkout(parent_commit)
        # open the changed files
        prompt = f'Below is an issue on {repo_name}.\n Issue:{conversation}\n\n and here are the files affected:\n'

        for file in changed_files:
            file_abs = os.path.join(f'{self.local_path}', file)
            prompt += 'Changed file: ' + file + '```'
            with open(file_abs, 'r') as f:
                prompt += f.read()
            prompt += '```\n'

        prompt += 'Please provide the patch to the above files to fix the issue.'

        patch = complete(prompt)
        return patch

class PR:
    def __init__(self, pr_num, repo):
        self.num = pr_num
        self.pr = repo.github.get_pull(pr_num)
        self.url = self.pr.html_url
        self.num_changed_files = self.pr.changed_files

        self.parent_commit = self.get_parent_commit()
        self.changed_files = self.get_changed_files()

        if len(self.changed_files) != self.num_changed_files:
            print(f"changed files for {self.url} don't match")

    def get_changed_files(self):
        # r = requests.get(f"https://github.com/{repo.full_name}/pull/{pr_num}/files")
        # soup = BeautifulSoup(r.text, 'html.parser')
        resp = session.get(f"{self.url}/files")
        resp.html.render()
        soup = BeautifulSoup(resp.html.html, 'html.parser')
        file_els = soup.select('.file-info a[title]')
        if file_els is None:
            return []

        return [el.attrs['title'] for el in file_els]

    def get_parent_commit(self):
        return self.pr.get_commits()[0].parents[0].sha


class Issue:
    def __init__(self, issue_num, repo):
        self.num = issue_num
        self.issue = repo.github.get_issue(issue_num)
        self.url = self.issue.html_url

        self.body = self.parse()
        self.embed = embed(self.body)

    def get_comments(self):
        return [comment.body for comment in self.issue.get_comments()]

    def parse(self):
        issue = self.issue
        title = issue.title
        body = issue.body

        conversation = 'Issue: ' + title + '\n' + body + 'Responses:\n'
        for comment in issue.get_comments():
            name = comment.user.login
            body = comment.body
            conversation += 'From {name}\n: {body}\n'.format(name=name, body=body)
        return conversation

if __name__ == '__main__':
    repo_org = 'twbs'
    repo_name = 'bootstrap'
    repo = Repo(repo_org, repo_name)

    for issue_num, pr_num in repo.issue_pr_map.items():
        issue_num = int(issue_num)

        issue = Issue(issue_num, repo)
        pr = PR(pr_num, repo)

        count_hits, count_misses = repo.calc_similarity_score(issue, pr)

        if count_hits + count_misses > 0:
            print(f"pr: {pr.url}")
            print(f"issue: {issue.url}")
            print(f"hit rate: {count_hits / (count_hits + count_misses)}")
            print(f"hits/misses: {count_hits}/{count_misses}")
        else:
            print(f"no hits or misses for {issue_num}")

        if count_hits > 0:
            diff_url = pr.pr.diff_url
            diff = requests.get(diff_url).text
            # patch = repo.check_fix_issue(issue, pr)
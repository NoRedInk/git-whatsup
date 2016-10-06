# git-whatsup

List up remote branches that conflict with the current working copy.

Requires Python 3.5+ and pygit2.

```
$ brew install libgit2
$ pip install git-whatsup
$ git-whatsup
conflicts with me
------------------------------------------------------------
origin/find-the-leaks (M!)
   spec/spec_helper.rb C
   app/assets/cactus.png deleted by us
```

How it works:

- Create a commit on top of the current index with all unstaged changes
- Tag the commit with `whatsup-with-me`
- For each remote branch,
  - Try merging with `whatsup-with-me`
  - If it conflicts, try merging with `origin/master`
  - Based on the results, classify into roughly these categories:
    no conflicts, conflicts with my changes, or conflicts with just master
- Output those that conflict with my changes
  - Output conflicting diffs too if requested


## Usage

```
$ git-whatsup --help
usage: git-whatsup [-h] [--remote REMOTE_NAME] [--master BRANCH_NAME]
                   [--branch BRANCH_NAME] [--all] [--diff]
                   [--format {plain,json}]
                   [repo_path]

List up remote branches that conflict with the current working copy.

positional arguments:
  repo_path             target Git repository

optional arguments:
  -h, --help            show this help message and exit
  --remote REMOTE_NAME  compare against branches in this remote
  --master BRANCH_NAME  master branch name
  --branch BRANCH_NAME, -b BRANCH_NAME
                        branches to check. by default, all branches are
                        checked
  --all, -a             output all statuses if output format is `plain`
  --diff, -d            output diffs if output format is `plain`
  --format {plain,json}, -f {plain,json}
                        json always includes diffs
```

## Assumptions and caveats

- Remote branches in your local clone are assumed to be up-to-date (`git fetch` has been run)
- Consider this alpha software

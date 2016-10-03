'''
Working copy management.
'''
import pygit2


WORKING_COPY_TAG_NAME = 'whatsup-with-me'
WORKING_COPY_TAG_REF = 'refs/tags/' + WORKING_COPY_TAG_NAME


def commit_to_working_copy_tag(repo: pygit2.Repository) -> pygit2.Oid:
    repo.index.read()
    repo.index.add_all()  # TODO: add a binding for update_all to pygit2
    tree = repo.index.write_tree()
    signature = repo.default_signature
    message = 'whats up with me'
    commit_oid = repo.create_commit(
        None,
        signature,
        signature,
        message,
        tree,
        [repo.head.get_object().hex])
    try:
        tag = get_working_copy_tag(repo)
        tag.set_target(commit_oid)
    except KeyError:
        repo.create_tag(
            WORKING_COPY_TAG_NAME,
            commit_oid,
            pygit2.GIT_OBJ_COMMIT,
            signature,
            message)

    return commit_oid


def get_working_copy_tag(repo: pygit2.Repository) -> pygit2.Reference:
    return repo.lookup_reference(WORKING_COPY_TAG_REF)

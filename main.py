import os
import yaml
import requests
import hashlib

cci_dir = '/Users/fernando/dev/conan-center-index'
recipes_dir = os.path.join(cci_dir, 'recipes')

def get_personal_token_from_env():
    token = os.environ.get('GITHUB_TOKEN')
    if token:
        return token
    else:
        print('GITHUB_TOKEN environment variable not found')
        return None

def get_recipe_dirs():
    for root, dirs, files in os.walk(recipes_dir):
        if 'config.yml' in files:
            yield root

def parse_config_yml(file):
    with open(file, 'r') as f:
        return yaml.safe_load(f)

def sort_versions_desc(versions):
    return sorted(versions, key=lambda x: x.split('.'), reverse=True)

def get_github_latest_tag_url(repo):
    url = f'https://api.github.com/repos/{repo}/tags'
    # print(f'url: {url}')
    return url

def get_github_latest_release_url(repo):
    url = f'https://api.github.com/repos/{repo}/releases/latest'
    # print(f'url: {url}')
    return url

def get_github_latest_tag_data(repo, personal_token=None):
    url = get_github_latest_tag_url(repo)
    headers = {}

    if personal_token:
        headers['Authorization'] = f'token {personal_token}'
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        # print(response.json()[0])
        return response.status_code, response.headers, response.json()[0]
    else:
        # print(f'url: {url} - status_code: {response.status_code} - Headers: {response.headers}')
        return response.status_code, response.headers, None


def get_github_latest_release_data(repo, personal_token=None):
    url = get_github_latest_release_url(repo)
    headers = {}

    if personal_token:
        headers['Authorization'] = f'token {personal_token}'
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.status_code, response.headers, response.json()
    else:
        # print(f'url: {url} - status_code: {response.status_code} - Headers: {response.headers}')
        return response.status_code, response.headers, None

def get_github_latest_data(repo, personal_token=None):
    status_code, headers, data = get_github_latest_release_data(repo, personal_token)
    if status_code == 200:
        return {
            'from': 'release',
            'version': data['tag_name'],
            'tarball_url': data['tarball_url']
        }
    else:
        status_code, headers, data = get_github_latest_tag_data(repo, personal_token)
        if status_code == 200:
            return {
                'from': 'tag',
                'version': data['name'],
                'tarball_url': data['tarball_url']
            }
        else:
            return None


def normalize_version(version):
    return version.replace('v', '')

def to_int_list(version):
    return [int(x) for x in version.split('.')]

def version_is_newer(version1, version2):
    return to_int_list(normalize_version(version1)) > to_int_list(normalize_version(version2))

def upgrade_conandata_yml(data, data_dir, latest_release_version, latest_release_url, sha256):
    sources = data['sources']
    sources.push(latest_release_version)

    sources[latest_release_version] = {
        'url': latest_release_url,
        'sha256': sha256
    }

    with open(os.path.join(data_dir, 'conandata.yml'), 'w') as f:
        yaml.dump(data, f)

def calculate_sha256sum(tarball_url):
    r = requests.get(tarball_url, stream=True)
    sha256 = hashlib.sha256()
    for chunk in r.iter_content(chunk_size=1024):
        sha256.update(chunk)
    return sha256.hexdigest()

def upgrade_recipe(recipe_dir, latest_release_version, latest_release_url):
    recipe_name = os.path.basename(recipe_dir)
    print(recipe_name)
    versions = parse_config_yml(os.path.join(recipe_dir, 'config.yml'))['versions']
    sorted_versions = sort_versions_desc(versions)

    last_version = sorted_versions[0]
    data_dir = os.path.join(recipe_dir, versions[last_version]['folder'])
    print(data_dir)

    data = parse_config_yml(os.path.join(data_dir, 'conandata.yml'))
    sha256 = calculate_sha256sum(latest_release_url)
    upgrade_conandata_yml(data, data_dir, latest_release_version, latest_release_url, sha256)

def process_recipe(recipe_dir):
    recipe_name = os.path.basename(recipe_dir)

    print('-' * 80)
    print(f'Recipe Name: {recipe_name}')
    print(f'Recipe Dir: {recipe_dir}')

    # if recipe_name != 'tinycthread':
    #     return True

    versions = parse_config_yml(os.path.join(recipe_dir, 'config.yml'))['versions']
    sorted_versions = sort_versions_desc(versions)

    last_version = sorted_versions[0]
    if last_version.startswith('cci'):
        print(f'Last version is a CCI version: {last_version}')
        return True

    data_dir = os.path.join(recipe_dir, versions[last_version]['folder'])
    # print(data_dir)

    data = parse_config_yml(os.path.join(data_dir, 'conandata.yml'))
    url = data['sources'][last_version]['url']
    # print(url)

    if 'github.com' in url:
        repo = url.split('github.com/')[1].split('/archive')[0]
        # print(repo)
        # print(get_github_latest_release_url(repo))
        latest_release_data = get_github_latest_data(repo, get_personal_token_from_env())
        # print(latest_release_data)
        if latest_release_data:

            latest_release_tag = latest_release_data['version']

            # print(f'Latest release tag: {latest_release_tag}')
            if version_is_newer(latest_release_tag, last_version):
                print(f'Update to latest release tag: {latest_release_tag}')
                latest_release_url = latest_release_data['tarball_url']
                # upgrade_recipe(recipe_dir, latest_release_tag, latest_release_url)
            else:
                print(f'Already using latest release tag, from GitHub: {latest_release_tag}, from CCI: {last_version}')

    else:
        print(f'Not a github for recipe {recipe_name} - url: {url}')

def main():
    for recipe_dir in get_recipe_dirs():
        x = process_recipe(recipe_dir)
        # if not x:
        #     return
        # return

if __name__ == '__main__':
    main()


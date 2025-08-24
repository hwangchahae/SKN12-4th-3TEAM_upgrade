"""
GitHub GraphQL API를 사용한 초고속 저장소 분석기
"""

import requests
import base64
from typing import List, Dict, Any
import os

class GitHubGraphQLFetcher:
    def __init__(self, repo_url: str, token: str = None):
        self.repo_url = repo_url
        self.token = token or os.environ.get("GITHUB_TOKEN")
        
        # GitHub GraphQL 엔드포인트
        self.graphql_url = "https://api.github.com/graphql"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        # 저장소 정보 파싱
        parts = repo_url.rstrip('/').split('/')
        self.owner = parts[-2]
        self.repo = parts[-1].replace('.git', '')
        
        self.api_call_count = 0
    
    def fetch_all_files_single_query(self) -> List[Dict[str, Any]]:
        """
        단일 GraphQL 쿼리로 모든 파일 내용 가져오기
        주의: 작은 저장소에만 적합 (GitHub은 응답 크기 제한이 있음)
        """
        
        # 먼저 파일 목록 가져오기
        query = """
        query($owner: String!, $repo: String!) {
          repository(owner: $owner, name: $repo) {
            defaultBranchRef {
              target {
                ... on Commit {
                  tree {
                    entries {
                      name
                      type
                      path
                      object {
                        ... on Blob {
                          text
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
        """
        
        variables = {
            "owner": self.owner,
            "repo": self.repo
        }
        
        response = requests.post(
            self.graphql_url,
            json={"query": query, "variables": variables},
            headers=self.headers
        )
        self.api_call_count += 1
        
        if response.status_code == 200:
            data = response.json()
            entries = data['data']['repository']['defaultBranchRef']['target']['tree']['entries']
            
            files = []
            for entry in entries:
                if entry['type'] == 'blob' and entry.get('object', {}).get('text'):
                    files.append({
                        'path': entry['path'],
                        'name': entry['name'],
                        'content': entry['object']['text']
                    })
            
            return files
        
        return []
    
    def fetch_files_in_batches(self, file_paths: List[str], batch_size: int = 10) -> List[Dict[str, Any]]:
        """
        여러 파일을 배치로 나누어 GraphQL로 가져오기
        대규모 저장소에 적합
        """
        
        files = []
        
        for i in range(0, len(file_paths), batch_size):
            batch = file_paths[i:i + batch_size]
            
            # 동적으로 쿼리 생성 (각 파일에 대한 별칭 사용)
            query_parts = []
            for idx, path in enumerate(batch):
                query_parts.append(f"""
                file{idx}: object(expression: "HEAD:{path}") {{
                  ... on Blob {{
                    text
                  }}
                }}
                """)
            
            query = f"""
            query($owner: String!, $repo: String!) {{
              repository(owner: $owner, name: $repo) {{
                {' '.join(query_parts)}
              }}
            }}
            """
            
            variables = {
                "owner": self.owner,
                "repo": self.repo
            }
            
            response = requests.post(
                self.graphql_url,
                json={"query": query, "variables": variables},
                headers=self.headers
            )
            self.api_call_count += 1
            
            if response.status_code == 200:
                data = response.json()
                repo_data = data['data']['repository']
                
                for idx, path in enumerate(batch):
                    file_data = repo_data.get(f'file{idx}')
                    if file_data and file_data.get('text'):
                        files.append({
                            'path': path,
                            'name': path.split('/')[-1],
                            'content': file_data['text']
                        })
            
            print(f"배치 {i//batch_size + 1} 완료: {len(batch)}개 파일")
        
        return files
    
    def fetch_repository_structure(self) -> Dict[str, Any]:
        """
        저장소 전체 구조를 한 번의 쿼리로 가져오기
        """
        
        query = """
        query($owner: String!, $repo: String!) {
          repository(owner: $owner, name: $repo) {
            defaultBranchRef {
              name
              target {
                ... on Commit {
                  tree {
                    entries {
                      name
                      type
                      path
                      object {
                        ... on Tree {
                          entries {
                            name
                            type
                            path
                          }
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
        """
        
        variables = {
            "owner": self.owner,
            "repo": self.repo
        }
        
        response = requests.post(
            self.graphql_url,
            json={"query": query, "variables": variables},
            headers=self.headers
        )
        self.api_call_count += 1
        
        if response.status_code == 200:
            return response.json()
        
        return {}
    
    def get_all_files_optimized(self) -> List[Dict[str, Any]]:
        """
        최적화된 방식으로 모든 파일 가져오기
        1. 먼저 구조 파악 (1 API call)
        2. 파일들을 배치로 가져오기 (n/10 API calls)
        """
        
        print(f"[GraphQL] 저장소 구조 분석 중...")
        
        # 1단계: 파일 목록 가져오기
        structure_query = """
        query($owner: String!, $repo: String!) {
          repository(owner: $owner, name: $repo) {
            object(expression: "HEAD:") {
              ... on Tree {
                entries {
                  name
                  type
                  path
                  object {
                    ... on Tree {
                      entries {
                        name
                        type
                        path
                        object {
                          ... on Tree {
                            entries {
                              name
                              type
                              path
                            }
                          }
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
        """
        
        variables = {
            "owner": self.owner,
            "repo": self.repo
        }
        
        response = requests.post(
            self.graphql_url,
            json={"query": structure_query, "variables": variables},
            headers=self.headers
        )
        self.api_call_count += 1
        
        # 파일 경로 수집
        file_paths = []
        
        def extract_files(entries, prefix=""):
            for entry in entries:
                if entry['type'] == 'blob':
                    # 주요 파일 확장자만 필터링
                    if any(entry['name'].endswith(ext) for ext in ['.py', '.js', '.md', '.ts', '.java']):
                        file_paths.append(entry['path'])
                elif entry['type'] == 'tree' and 'object' in entry:
                    extract_files(entry['object'].get('entries', []))
        
        if response.status_code == 200:
            data = response.json()
            entries = data['data']['repository']['object']['entries']
            extract_files(entries)
        
        print(f"[GraphQL] {len(file_paths)}개 파일 발견")
        
        # 2단계: 배치로 파일 내용 가져오기
        files = self.fetch_files_in_batches(file_paths, batch_size=20)
        
        print(f"[GraphQL] 완료: {len(files)}개 파일, {self.api_call_count}회 API 호출")
        
        return files


# 테스트 코드
if __name__ == "__main__":
    import time
    
    # 토큰 로드
    from pathlib import Path
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if line.startswith("GITHUB_TOKEN="):
                    token = line.split("=", 1)[1].strip()
                    os.environ["GITHUB_TOKEN"] = token
                    break
    
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GitHub 토큰이 필요합니다!")
        exit(1)
    
    repo_url = "https://github.com/pallets/click"
    
    print("\n" + "="*60)
    print("GitHub GraphQL API 성능 테스트")
    print("="*60)
    
    fetcher = GitHubGraphQLFetcher(repo_url, token)
    
    start = time.time()
    files = fetcher.get_all_files_optimized()
    elapsed = time.time() - start
    
    print("\n" + "="*60)
    print("결과:")
    print(f"- 시간: {elapsed:.2f}초")
    print(f"- 파일: {len(files)}개")
    print(f"- API 호출: {fetcher.api_call_count}회")
    print(f"- 효율성: {len(files) / fetcher.api_call_count:.1f} 파일/API호출")
    print("="*60)
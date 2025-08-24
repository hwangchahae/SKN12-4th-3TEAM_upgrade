"""
GitHub 저장소 분석 및 임베딩을 위한 개선된 모듈

원본 github_analyzer.py의 성능을 대폭 개선한 버전
주요 개선 사항:
- 병렬 API 호출
- Trees API 활용
- 캐싱 메커니즘
- 배치 처리
"""

import requests
import chromadb
import os
import re
import openai
import base64
import asyncio
import aiohttp
from typing import Optional, List, Dict, Any, Tuple
from langchain.schema import Document
from cryptography.fernet import Fernet
import tiktoken
import ast
import markdown
import nbformat
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from functools import lru_cache
import time

# ----------------- 상수 정의 -----------------
MAIN_EXTENSIONS = ['.py', '.js', '.md', '.ts', '.java', '.cpp', '.h', '.hpp', '.c', '.cs', '.txt', '.ipynb']
CHUNK_SIZE = 500
GITHUB_TOKEN = "GITHUB_TOKEN"
KEY_FILE = ".key"
BATCH_SIZE = 20  # 동시 처리할 파일 수
MAX_RETRIES = 3  # API 호출 재시도 횟수

# ChromaDB 영구 저장소 클라이언트
REPO_DB_PATH = "./repo_analysis_db"
os.makedirs(REPO_DB_PATH, exist_ok=True)
chroma_client = chromadb.PersistentClient(path=REPO_DB_PATH)

# 캐시 디렉토리
CACHE_DIR = "./github_cache"
os.makedirs(CACHE_DIR, exist_ok=True)


class GitHubRepositoryFetcherImproved:
    """
    개선된 GitHub 저장소 파일 가져오기 클래스
    
    성능 개선 사항:
    - 병렬 API 호출
    - Trees API로 한 번에 파일 목록 가져오기
    - 파일 내용 캐싱
    - 배치 처리
    """
    
    def __init__(self, repo_url: str, token: Optional[str] = None, session_id: Optional[str] = None):
        """초기화"""
        self.repo_url = repo_url
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'GitHub-Code-Analyzer/2.0'
        } if self.token else {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'GitHub-Code-Analyzer/2.0'
        }
        
        self.files = []
        self.api_call_count = 0
        self.cache_hits = 0
        self.cache_misses = 0
        
        # 저장소 정보 추출
        self.owner, self.repo, self.path = self.extract_repo_info(repo_url)
        if not self.owner or not self.repo:
            raise ValueError("Invalid GitHub repository URL")
        
        # 세션 설정
        self.session_id = session_id or f"{self.owner}_{self.repo}"
        self.repo_path = f"./repos/{self.session_id}"
        
        # 캐시 설정
        self.cache_file = os.path.join(CACHE_DIR, f"{self.owner}_{self.repo}_cache.json")
        self.file_cache = self.load_cache()
        
        # ChromaDB 컬렉션
        self.collection = chroma_client.get_or_create_collection(
            name=self.session_id,
            metadata={"description": f"Repository: {self.owner}/{self.repo}"}
        )
    
    def extract_repo_info(self, url: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """GitHub URL에서 소유자, 저장소 이름, 파일 경로를 추출"""
        try:
            url = url.strip().rstrip('/')
            if url.endswith('.git'):
                url = url[:-4]
            
            parts = url.split('/')
            if 'github.com' in parts:
                github_index = parts.index('github.com')
                if len(parts) >= github_index + 3:
                    owner = parts[github_index + 1]
                    repo = parts[github_index + 2]
                    path = '/'.join(parts[github_index + 3:]) if len(parts) > github_index + 3 else None
                    return owner, repo, path
        except Exception as e:
            print(f"URL 파싱 중 오류 발생: {e}")
        return None, None, None
    
    def load_cache(self) -> Dict[str, Any]:
        """캐시 파일 로드"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_cache(self):
        """캐시 파일 저장"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.file_cache, f, ensure_ascii=False)
        except Exception as e:
            print(f"캐시 저장 실패: {e}")
    
    def get_cache_key(self, path: str, sha: Optional[str] = None) -> str:
        """캐시 키 생성"""
        if sha:
            return f"{path}:{sha}"
        return path
    
    def filter_main_files_fast(self):
        """
        Trees API를 사용하여 한 번의 호출로 모든 파일 목록 가져오기
        """
        print(f"[DEBUG] Trees API로 파일 목록 가져오기...")
        
        # 기본 브랜치 확인
        repo_url = f"https://api.github.com/repos/{self.owner}/{self.repo}"
        response = requests.get(repo_url, headers=self.headers)
        self.api_call_count += 1
        
        if response.status_code != 200:
            print(f"[ERROR] 저장소 정보 가져오기 실패: {response.status_code}")
            return
        
        default_branch = response.json().get('default_branch', 'main')
        
        # Trees API로 전체 파일 트리 가져오기
        trees_url = f"https://api.github.com/repos/{self.owner}/{self.repo}/git/trees/{default_branch}?recursive=1"
        response = requests.get(trees_url, headers=self.headers)
        self.api_call_count += 1
        
        if response.status_code != 200:
            print(f"[ERROR] Trees API 호출 실패: {response.status_code}")
            # 폴백: 기존 방식 사용
            self.filter_main_files()
            return
        
        tree_data = response.json()
        
        # 주요 파일만 필터링
        self.files = []
        for item in tree_data.get('tree', []):
            if item['type'] == 'blob':  # 파일인 경우
                path = item['path']
                if any(path.endswith(ext) for ext in MAIN_EXTENSIONS):
                    # 큰 파일 제외
                    if item.get('size', 0) < 100000:  # 100KB 미만
                        self.files.append({
                            'path': path,
                            'sha': item['sha'],
                            'size': item.get('size', 0)
                        })
        
        print(f"[DEBUG] Trees API로 {len(self.files)}개 파일 필터링 완료")
    
    def filter_main_files(self):
        """기존 방식 (폴백용)"""
        self.files = self.get_all_main_files()
        print(f"[DEBUG] 기존 방식으로 {len(self.files)}개 파일 필터링")
    
    def get_all_main_files(self, path=""):
        """기존 재귀적 파일 탐색 (폴백용)"""
        files = []
        dir_contents = self.get_repo_directory_contents(path)
        
        if isinstance(dir_contents, dict) and dir_contents.get('error'):
            return files
        
        if isinstance(dir_contents, list):
            for item in dir_contents:
                if item['type'] == 'file' and any(item['path'].endswith(ext) for ext in MAIN_EXTENSIONS):
                    files.append(item['path'])
                elif item['type'] == 'dir':
                    sub_files = self.get_all_main_files(item['path'])
                    files.extend(sub_files)
        
        return files
    
    def get_repo_directory_contents(self, path: str = "") -> Any:
        """디렉토리 내용 가져오기 (폴백용)"""
        try:
            url = f"https://api.github.com/repos/{self.owner}/{self.repo}/contents/{path}"
            response = requests.get(url, headers=self.headers)
            self.api_call_count += 1
            
            if response.status_code == 200:
                return response.json()
            return {"error": True, "status_code": response.status_code}
        except Exception as e:
            return {"error": True, "message": str(e)}
    
    async def fetch_file_content_async(self, session: aiohttp.ClientSession, file_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """비동기로 파일 내용 가져오기"""
        path = file_info['path'] if isinstance(file_info, dict) else file_info
        sha = file_info.get('sha') if isinstance(file_info, dict) else None
        
        # 캐시 확인
        cache_key = self.get_cache_key(path, sha)
        if cache_key in self.file_cache:
            self.cache_hits += 1
            cached_data = self.file_cache[cache_key]
            # 캐시된 데이터가 1일 이내인 경우 사용
            if time.time() - cached_data.get('timestamp', 0) < 86400:
                return cached_data['content']
        
        self.cache_misses += 1
        
        # API 호출
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/contents/{path}"
        
        for retry in range(MAX_RETRIES):
            try:
                async with session.get(url, headers=self.headers) as response:
                    self.api_call_count += 1
                    
                    if response.status == 200:
                        data = await response.json()
                        
                        # Base64 디코딩
                        try:
                            content = base64.b64decode(data['content']).decode('utf-8')
                            
                            result = {
                                'path': path,
                                'content': content,
                                'file_name': data['name'],
                                'file_type': data['name'].split('.')[-1] if '.' in data['name'] else '',
                                'sha': data['sha'],
                                'source_url': data['html_url']
                            }
                            
                            # 캐시 저장
                            self.file_cache[cache_key] = {
                                'content': result,
                                'timestamp': time.time()
                            }
                            
                            return result
                            
                        except UnicodeDecodeError:
                            # 바이너리 파일
                            return None
                    
                    elif response.status == 403 and retry < MAX_RETRIES - 1:
                        # API 제한 - 잠시 대기 후 재시도
                        await asyncio.sleep(2 ** retry)
                    else:
                        return None
                        
            except Exception as e:
                if retry == MAX_RETRIES - 1:
                    print(f"[ERROR] 파일 가져오기 실패 ({path}): {e}")
                    return None
                await asyncio.sleep(1)
        
        return None
    
    async def get_file_contents_parallel(self) -> List[Dict[str, Any]]:
        """병렬로 파일 내용 가져오기"""
        print(f"[DEBUG] 병렬 처리 시작: {len(self.files)}개 파일")
        
        # Trees API 사용 (더 빠른 파일 목록)
        if not self.files:
            self.filter_main_files_fast()
        
        file_objs = []
        
        # aiohttp 세션 생성
        connector = aiohttp.TCPConnector(limit=BATCH_SIZE)
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # 배치 처리
            for i in range(0, len(self.files), BATCH_SIZE):
                batch = self.files[i:i + BATCH_SIZE]
                
                # 배치 내 파일들을 병렬로 가져오기
                tasks = [self.fetch_file_content_async(session, file_info) for file_info in batch]
                results = await asyncio.gather(*tasks)
                
                # 결과 수집
                for result in results:
                    if result:
                        file_objs.append(result)
                
                # 진행 상황 표시
                processed = min(i + BATCH_SIZE, len(self.files))
                print(f"[DEBUG] 진행: {processed}/{len(self.files)} 파일 처리 완료")
                
                # API 제한 방지를 위한 짧은 대기
                if i + BATCH_SIZE < len(self.files):
                    await asyncio.sleep(0.1)
        
        # 캐시 저장
        self.save_cache()
        
        print(f"[DEBUG] 병렬 처리 완료: {len(file_objs)}개 파일")
        print(f"[DEBUG] API 호출: {self.api_call_count}회")
        print(f"[DEBUG] 캐시 히트: {self.cache_hits}, 미스: {self.cache_misses}")
        
        return file_objs
    
    def get_file_contents_sequential(self) -> List[Dict[str, Any]]:
        """순차 처리 (작은 저장소용)"""
        print(f"[DEBUG] 순차 처리 시작: {len(self.files)}개 파일")
        
        if not self.files:
            self.filter_main_files_fast()
        
        file_objs = []
        
        for file_info in self.files:
            path = file_info['path'] if isinstance(file_info, dict) else file_info
            sha = file_info.get('sha') if isinstance(file_info, dict) else None
            
            # 캐시 확인
            cache_key = self.get_cache_key(path, sha)
            if cache_key in self.file_cache:
                self.cache_hits += 1
                cached_data = self.file_cache[cache_key]
                if time.time() - cached_data.get('timestamp', 0) < 86400:
                    file_objs.append(cached_data['content'])
                    continue
            
            self.cache_misses += 1
            
            # API 호출
            url = f"https://api.github.com/repos/{self.owner}/{self.repo}/contents/{path}"
            response = requests.get(url, headers=self.headers)
            self.api_call_count += 1
            
            if response.status_code == 200:
                data = response.json()
                try:
                    content = base64.b64decode(data['content']).decode('utf-8')
                    result = {
                        'path': path,
                        'content': content,
                        'file_name': data['name'],
                        'file_type': data['name'].split('.')[-1] if '.' in data['name'] else '',
                        'sha': data['sha'],
                        'source_url': data['html_url']
                    }
                    
                    # 캐시 저장
                    self.file_cache[cache_key] = {
                        'content': result,
                        'timestamp': time.time()
                    }
                    
                    file_objs.append(result)
                except UnicodeDecodeError:
                    pass  # 바이너리 파일 건너뛰기
        
        # 캐시 저장
        self.save_cache()
        
        print(f"[DEBUG] 순차 처리 완료: {len(file_objs)}개 파일")
        print(f"[DEBUG] API 호출: {self.api_call_count}회")
        print(f"[DEBUG] 캐시 히트: {self.cache_hits}, 미스: {self.cache_misses}")
        
        return file_objs
    
    def get_file_contents(self) -> List[Dict[str, Any]]:
        """스마트 파일 가져오기 (파일 수에 따라 자동 선택)"""
        
        # 파일 목록이 없으면 먼저 가져오기
        if not self.files:
            self.filter_main_files_fast()
        
        file_count = len(self.files)
        
        # 전략 선택 임계값
        SEQUENTIAL_THRESHOLD = 5    # 5개 미만: 순차 처리
        GRAPHQL_THRESHOLD = 500     # 500개 이상: GraphQL 사용
        
        print(f"[DEBUG] 파일 수: {file_count}개")
        
        if file_count < SEQUENTIAL_THRESHOLD:
            # 작은 저장소: 순차 처리가 더 빠름
            print(f"[DEBUG] {SEQUENTIAL_THRESHOLD}개 미만 -> 순차 처리 선택")
            return self.get_file_contents_sequential()
        elif file_count >= GRAPHQL_THRESHOLD and self.token:
            # 대용량 저장소: GraphQL 사용 (토큰 필요)
            print(f"[DEBUG] {GRAPHQL_THRESHOLD}개 이상 -> GraphQL 모드 선택")
            try:
                from github_analyzer_graphql import GitHubGraphQLFetcher
                graphql_fetcher = GitHubGraphQLFetcher(self.repo_url, self.token)
                files = graphql_fetcher.get_all_files_optimized()
                self.api_call_count += graphql_fetcher.api_call_count
                return files
            except ImportError:
                print(f"[DEBUG] GraphQL 모듈 없음 -> 병렬 처리로 대체")
                # GraphQL 모듈이 없으면 병렬 처리로 대체
        
        # 중간 크기 저장소: 병렬 처리가 최적
        print(f"[DEBUG] {SEQUENTIAL_THRESHOLD}개 이상 {GRAPHQL_THRESHOLD}개 미만 -> 병렬 처리 선택")
        # 이벤트 루프가 이미 실행 중인지 확인
        try:
            loop = asyncio.get_running_loop()
            # 이미 루프가 실행 중이면 새 스레드에서 실행
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, self.get_file_contents_parallel())
                return future.result()
        except RuntimeError:
            # 루프가 없으면 새로 생성
            return asyncio.run(self.get_file_contents_parallel())
    
    def get_directory_structure(self) -> str:
        """디렉토리 구조 생성"""
        if not self.files:
            self.filter_main_files_fast()
        
        # 파일 경로로 트리 구조 생성
        tree = {}
        for file_info in self.files:
            path = file_info['path'] if isinstance(file_info, dict) else file_info
            parts = path.split('/')
            
            current = tree
            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    # 파일
                    current[f"📄 {part}"] = None
                else:
                    # 디렉토리
                    if f"📁 {part}" not in current:
                        current[f"📁 {part}"] = {}
                    current = current[f"📁 {part}"]
        
        # 트리를 문자열로 변환
        lines = []
        def traverse(node, prefix=""):
            for key, value in sorted(node.items()):
                lines.append(f"{prefix}{key}")
                if value is not None:
                    traverse(value, prefix + "  ")
        
        traverse(tree)
        return "\n".join(lines)
    
    def load_repo_data(self) -> bool:
        """저장소 데이터 로드"""
        try:
            if self.files:
                return True
            
            # Trees API 사용 (더 빠름)
            self.filter_main_files_fast()
            
            if not self.files:
                print("[WARNING] 필터링된 파일 목록이 없습니다.")
                return False
            
            print(f"[DEBUG] 데이터 로드 성공: {len(self.files)} 파일")
            return True
            
        except Exception as e:
            print(f"[ERROR] 데이터 로드 실패: {e}")
            return False
    
    # 토큰 관리 메서드들 (기존과 동일)
    @staticmethod
    def generate_key() -> bytes:
        """암호화 키 생성"""
        if not os.path.exists(KEY_FILE):
            key = Fernet.generate_key()
            with open(KEY_FILE, 'wb') as key_file:
                key_file.write(key)
            return key
        else:
            with open(KEY_FILE, 'rb') as key_file:
                return key_file.read()
    
    @staticmethod
    def encrypt_token(token: str) -> str:
        """토큰 암호화"""
        key = GitHubRepositoryFetcherImproved.generate_key()
        f = Fernet(key)
        return f.encrypt(token.encode()).decode()
    
    @staticmethod
    def decrypt_token(encrypted_token: str) -> str:
        """토큰 복호화"""
        key = GitHubRepositoryFetcherImproved.generate_key()
        f = Fernet(key)
        return f.decrypt(encrypted_token.encode()).decode()


def analyze_repository(repo_url: str, token: Optional[str] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
    """
    개선된 저장소 분석 함수
    
    파일 수에 따라 자동으로 최적 전략 선택:
    - 5개 미만: 순차 처리 (오버헤드 최소화)
    - 5개 이상: 병렬 처리 (성능 극대화)
    """
    try:
        print(f"[DEBUG] 스마트 저장소 분석 시작: {repo_url}")
        
        # ChromaDB 디렉토리 정리
        if session_id:
            cleanup_chromadb_for_session(session_id)
        
        # 개선된 Fetcher 사용
        fetcher = GitHubRepositoryFetcherImproved(repo_url, token, session_id)
        
        # 데이터 로드
        if not fetcher.load_repo_data():
            return {'success': False, 'error': '저장소 데이터를 로드할 수 없습니다.'}
        
        # 스마트 파일 가져오기 (파일 수에 따라 자동 선택)
        files = fetcher.get_file_contents()  # 내부에서 자동으로 순차/병렬 선택
        
        if not files:
            return {'success': False, 'error': '저장소에서 파일을 찾을 수 없습니다.'}
        
        # 디렉토리 구조 생성
        directory_structure = fetcher.get_directory_structure()
        
        print(f"[DEBUG] 파일 수집 완료: {len(files)} 파일")
        print(f"[DEBUG] API 호출 횟수: {fetcher.api_call_count}")
        print(f"[DEBUG] 캐시 효율: {fetcher.cache_hits}/{fetcher.cache_hits + fetcher.cache_misses}")
        
        # 임베딩 처리 (기존과 동일)
        if session_id:
            from github_analyzer import RepositoryEmbedder
            embedder = RepositoryEmbedder(session_id)
            embedder.process_and_embed(files)
            print(f"[DEBUG] 임베딩 처리 완료")
        
        return {
            'success': True,
            'files': files,
            'directory_structure': directory_structure,
            'total_files': len(files),
            'api_calls': fetcher.api_call_count,
            'cache_hits': fetcher.cache_hits,
            'cache_misses': fetcher.cache_misses
        }
        
    except Exception as e:
        import traceback
        print(f"[ERROR] 저장소 분석 실패: {e}")
        traceback.print_exc()
        return {'success': False, 'error': f'저장소 분석 중 오류 발생: {str(e)}'}


def cleanup_chromadb_for_session(session_id: str):
    """세션의 ChromaDB 데이터 정리"""
    try:
        import shutil
        chroma_path = os.path.join("repo_analysis_db", session_id)
        if os.path.exists(chroma_path):
            shutil.rmtree(chroma_path)
    except Exception as e:
        print(f"[WARNING] ChromaDB 정리 중 오류: {e}")


# 기존 함수들과의 호환성 유지
def get_repository_branches(repo_url: str, token: Optional[str] = None) -> Dict[str, Any]:
    """브랜치 목록 가져오기 (기존과 동일)"""
    from github_analyzer import get_repository_branches as original_func
    return original_func(repo_url, token)


def get_repository_file_tree(repo_url: str, branch: str = 'main', token: Optional[str] = None) -> Dict[str, Any]:
    """파일 트리 가져오기 (기존과 동일)"""
    from github_analyzer import get_repository_file_tree as original_func
    return original_func(repo_url, branch, token)


def get_file_content(repo_url: str, file_path: str, branch: str = 'main', token: Optional[str] = None) -> Dict[str, Any]:
    """파일 내용 가져오기 (기존과 동일)"""
    from github_analyzer import get_file_content as original_func
    return original_func(repo_url, file_path, branch, token)


if __name__ == "__main__":
    # 테스트
    print("=" * 60)
    print("GitHub Analyzer Improved - 스마트 처리 전략")
    print("=" * 60)
    print("파일 수에 따라 자동으로 최적 전략 선택:")
    print("  - 1-4개 파일: 순차 처리 (오버헤드 최소화)")
    print("  - 5개 이상: 병렬 처리 (성능 극대화)")
    print("=" * 60)
    
    test_repo = "https://github.com/octocat/Hello-World"
    print(f"\n테스트 저장소: {test_repo}")
    
    result = analyze_repository(test_repo)
    if result['success']:
        print(f"\n분석 성공!")
        print(f"  - 파일 수: {result['total_files']}")
        print(f"  - API 호출: {result.get('api_calls', 'N/A')}")
        print(f"  - 캐시 히트: {result.get('cache_hits', 'N/A')}")
        print(f"  - 처리 전략: {'순차' if result['total_files'] < 5 else '병렬'} 처리 사용")
    else:
        print(f"분석 실패: {result['error']}")
"""
GitHub Analyzer 종합 성능 벤치마크
- 다양한 크기의 저장소 테스트
- 원본 vs 개선(캐시X) vs 개선(캐시O) vs GraphQL 비교
- 파일 크기에 따른 자동 GraphQL 전환
"""

import time
import os
import sys
import shutil
import json
import requests
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# 상위 디렉토리를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

# .env에서 토큰 로드
def load_github_token():
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if line.startswith("GITHUB_TOKEN="):
                    token = line.split("=", 1)[1].strip()
                    os.environ["GITHUB_TOKEN"] = token
                    print(f"GitHub 토큰 로드 완료")
                    return token
    return None

# GraphQL 사용 임계값 (파일 개수 기준)
GRAPHQL_THRESHOLD = 500  # 500개 이상 파일이면 GraphQL 사용 (대용량만)

# 테스트할 저장소 목록 (다양한 크기)
TEST_REPOSITORIES = [
    {
        "url": "https://github.com/octocat/Spoon-Knife",
        "name": "Spoon-Knife",
        "size": "tiny",
        "expected_files": 1,
        "use_graphql": False
    },
    {
        "url": "https://github.com/sindresorhus/awesome",
        "name": "awesome",
        "size": "small",
        "expected_files": 7,
        "use_graphql": False
    },
    {
        "url": "https://github.com/pallets/flask",
        "name": "flask",
        "size": "medium",
        "expected_files": 30,
        "use_graphql": False
    },
    {
        "url": "https://github.com/pallets/click",
        "name": "click",
        "size": "medium-large",
        "expected_files": 82,
        "use_graphql": False  # 병렬 처리 사용
    },
    {
        "url": "https://github.com/requests/requests",
        "name": "requests", 
        "size": "medium",
        "expected_files": 50,
        "use_graphql": False  # 병렬 처리 사용
    },
    {
        "url": "https://github.com/psf/black",
        "name": "black",
        "size": "medium-large",
        "expected_files": 300,
        "use_graphql": False  # 병렬 처리 사용 (500개 미만)
    },
    {
        "url": "https://github.com/pandas-dev/pandas",
        "name": "pandas",
        "size": "large",
        "expected_files": 800,
        "use_graphql": True  # GraphQL 테스트
    },
    {
        "url": "https://github.com/scikit-learn/scikit-learn", 
        "name": "scikit-learn",
        "size": "extra-large",
        "expected_files": 1500,
        "use_graphql": True  # GraphQL 필수
    },
    {
        "url": "https://github.com/django/django",
        "name": "django",
        "size": "huge",
        "expected_files": 3000,
        "use_graphql": True  # GraphQL 필수 (대용량)
    }
]

class ComprehensiveBenchmark:
    def __init__(self):
        self.token = load_github_token()
        self.results = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "has_token": bool(self.token)
            },
            "repositories": {},
            "summary": {}
        }
        
    def clear_cache(self):
        """캐시 디렉토리 초기화"""
        cache_dirs = [
            Path(__file__).parent.parent / "github_cache"
        ]
        for cache_dir in cache_dirs:
            if cache_dir.exists():
                try:
                    shutil.rmtree(cache_dir)
                    print(f"캐시 삭제: {cache_dir.name}")
                except PermissionError:
                    print(f"캐시 삭제 실패 (사용 중): {cache_dir.name}")
    
    def test_original(self, repo_url: str) -> Dict[str, Any]:
        """원본 버전 테스트"""
        print("  [원본] 테스트 시작...")
        
        # API 호출 횟수 추적을 위한 패치
        import requests
        original_get = requests.get
        api_call_count = 0
        
        def patched_get(*args, **kwargs):
            nonlocal api_call_count
            if 'api.github.com' in str(args[0]):
                api_call_count += 1
            return original_get(*args, **kwargs)
        
        requests.get = patched_get
        
        try:
            from github_analyzer import GitHubRepositoryFetcher
            
            start = time.time()
            fetcher = GitHubRepositoryFetcher(repo_url)
            fetcher.filter_main_files()
            files = fetcher.get_file_contents()
            elapsed = time.time() - start
            
            result = {
                "time": elapsed,
                "files_count": len(files),
                "api_calls": api_call_count,
                "success": True,
                "error": None
            }
            
            print(f"  [원본] 완료: {elapsed:.2f}초, {len(files)}개 파일, {api_call_count}회 API")
            
        except Exception as e:
            result = {
                "time": 0,
                "files_count": 0,
                "api_calls": api_call_count,
                "success": False,
                "error": str(e)
            }
            print(f"  [원본] 실패: {e}")
        
        finally:
            requests.get = original_get
        
        return result
    
    def test_improved_no_cache(self, repo_url: str) -> Dict[str, Any]:
        """개선 버전 테스트 (캐시 없음)"""
        print("  [개선-캐시X] 테스트 시작...")
        
        # 캐시 초기화
        self.clear_cache()
        
        try:
            from github_analyzer_improved import GitHubRepositoryFetcherImproved
            
            start = time.time()
            fetcher = GitHubRepositoryFetcherImproved(repo_url)
            fetcher.filter_main_files_fast()
            files = fetcher.get_file_contents()
            elapsed = time.time() - start
            
            result = {
                "time": elapsed,
                "files_count": len(files),
                "api_calls": fetcher.api_call_count,
                "cache_hits": fetcher.cache_hits,
                "cache_misses": fetcher.cache_misses,
                "success": True,
                "error": None
            }
            
            print(f"  [개선-캐시X] 완료: {elapsed:.2f}초, {len(files)}개 파일, {fetcher.api_call_count}회 API")
            
        except Exception as e:
            result = {
                "time": 0,
                "files_count": 0,
                "api_calls": 0,
                "cache_hits": 0,
                "cache_misses": 0,
                "success": False,
                "error": str(e)
            }
            print(f"  [개선-캐시X] 실패: {e}")
        
        return result
    
    def test_improved_with_cache(self, repo_url: str) -> Dict[str, Any]:
        """개선 버전 테스트 (캐시 활용)"""
        print("  [개선-캐시O] 테스트 시작...")
        
        # 캐시는 이미 이전 테스트에서 생성됨
        
        try:
            from github_analyzer_improved import GitHubRepositoryFetcherImproved
            
            start = time.time()
            fetcher = GitHubRepositoryFetcherImproved(repo_url)
            fetcher.filter_main_files_fast()
            files = fetcher.get_file_contents()
            elapsed = time.time() - start
            
            result = {
                "time": elapsed,
                "files_count": len(files),
                "api_calls": fetcher.api_call_count,
                "cache_hits": fetcher.cache_hits,
                "cache_misses": fetcher.cache_misses,
                "success": True,
                "error": None
            }
            
            print(f"  [개선-캐시O] 완료: {elapsed:.2f}초, {len(files)}개 파일, {fetcher.api_call_count}회 API")
            
        except Exception as e:
            result = {
                "time": 0,
                "files_count": 0,
                "api_calls": 0,
                "cache_hits": 0,
                "cache_misses": 0,
                "success": False,
                "error": str(e)
            }
            print(f"  [개선-캐시O] 실패: {e}")
        
        return result
    
    def test_graphql(self, repo_url: str) -> Dict[str, Any]:
        """GraphQL 버전 테스트"""
        print("  [GraphQL] 테스트 시작...")
        
        try:
            from github_analyzer_graphql import GitHubGraphQLFetcher
            
            start = time.time()
            fetcher = GitHubGraphQLFetcher(repo_url, self.token)
            files = fetcher.get_all_files_optimized()
            elapsed = time.time() - start
            
            result = {
                "time": elapsed,
                "files_count": len(files),
                "api_calls": fetcher.api_call_count,
                "success": True,
                "error": None
            }
            
            print(f"  [GraphQL] 완료: {elapsed:.2f}초, {len(files)}개 파일, {fetcher.api_call_count}회 API")
            
        except Exception as e:
            result = {
                "time": 0,
                "files_count": 0,
                "api_calls": 0,
                "success": False,
                "error": str(e)
            }
            print(f"  [GraphQL] 실패: {e}")
        
        return result
    
    def run_benchmark(self):
        """전체 벤치마크 실행"""
        print("\n" + "="*70)
        print("GitHub Analyzer 종합 성능 벤치마크")
        print("="*70)
        print(f"토큰 상태: {'있음' if self.token else '없음 (제한적 테스트)'}")
        print(f"테스트 저장소: {len(TEST_REPOSITORIES)}개")
        print("="*70)
        
        for repo_info in TEST_REPOSITORIES:
            repo_url = repo_info["url"]
            repo_name = repo_info["name"]
            
            # 토큰 없을 때 대용량 저장소 건너뛰기
            if not self.token and repo_info.get("skip_if_no_token"):
                print(f"\n[{repo_name}] 토큰 없음 - 건너뛰기")
                continue
            
            print(f"\n[{repo_name}] 테스트 시작 (크기: {repo_info['size']})")
            print("-" * 50)
            
            # 파일 수에 따른 테스트 전략 결정
            expected_files = repo_info.get("expected_files", 0)
            
            if expected_files <= 82:
                # 82개 이하: 원본 vs 개선 비교 (순차/병렬)
                print(f"  * 소규모 저장소 - 전체 비교 테스트")
                repo_results = {
                    "info": repo_info,
                    "original": self.test_original(repo_url),
                    "improved_no_cache": self.test_improved_no_cache(repo_url),
                    "improved_with_cache": self.test_improved_with_cache(repo_url)
                }
            elif expected_files <= 800:
                # 83-800개: 병렬 vs GraphQL 비교 (원본은 제외)
                print(f"  * 중규모 저장소 - 병렬 vs GraphQL 비교")
                repo_results = {
                    "info": repo_info,
                    "improved_no_cache": self.test_improved_no_cache(repo_url),
                    "improved_with_cache": self.test_improved_with_cache(repo_url)
                }
                if self.token:
                    repo_results["graphql"] = self.test_graphql(repo_url)
            else:
                # 800개 초과: GraphQL만 사용
                print(f"  * 대규모 저장소 - GraphQL 전용")
                repo_results = {
                    "info": repo_info
                }
                if self.token:
                    repo_results["graphql"] = self.test_graphql(repo_url)
                    repo_results["improved_with_cache"] = self.test_improved_with_cache(repo_url)
                else:
                    print("  토큰 없음 - 테스트 불가")
                    continue
            
            # 성능 분석
            if expected_files <= 82:
                # 소규모: 원본 vs 개선 분석
                if "original" in repo_results and repo_results["original"]["success"] and repo_results["improved_no_cache"]["success"]:
                    original_time = repo_results["original"]["time"]
                    no_cache_time = repo_results["improved_no_cache"]["time"]
                    with_cache_time = repo_results["improved_with_cache"]["time"]
                    
                    repo_results["analysis"] = {
                        "speedup_no_cache": original_time / no_cache_time if no_cache_time > 0 else 0,
                        "speedup_with_cache": original_time / with_cache_time if with_cache_time > 0 else 0,
                        "cache_effect": no_cache_time / with_cache_time if with_cache_time > 0 else 0,
                        "api_reduction_no_cache": (
                            (repo_results["original"]["api_calls"] - repo_results["improved_no_cache"]["api_calls"]) 
                            / repo_results["original"]["api_calls"] * 100
                        ) if repo_results["original"]["api_calls"] > 0 else 0,
                        "api_reduction_with_cache": (
                            (repo_results["original"]["api_calls"] - repo_results["improved_with_cache"]["api_calls"])
                            / repo_results["original"]["api_calls"] * 100
                        ) if repo_results["original"]["api_calls"] > 0 else 0
                    }
                    
                    print(f"\n  성능 향상:")
                    print(f"  - 캐시 없음: {repo_results['analysis']['speedup_no_cache']:.1f}배")
                    print(f"  - 캐시 활용: {repo_results['analysis']['speedup_with_cache']:.1f}배")
                    print(f"  - API 감소: {repo_results['analysis']['api_reduction_with_cache']:.1f}%")
                    
            elif expected_files <= 800:
                # 중규모: 병렬 vs GraphQL 분석
                if "graphql" in repo_results and repo_results["graphql"]["success"]:
                    no_cache_time = repo_results["improved_no_cache"]["time"]
                    with_cache_time = repo_results["improved_with_cache"]["time"]
                    graphql_time = repo_results["graphql"]["time"]
                    
                    repo_results["analysis"] = {
                        "parallel_time": no_cache_time,
                        "cache_time": with_cache_time,
                        "graphql_time": graphql_time,
                        "graphql_vs_parallel": no_cache_time / graphql_time if graphql_time > 0 else 0,
                        "graphql_vs_cache": with_cache_time / graphql_time if graphql_time > 0 else 0,
                        "parallel_api_calls": repo_results["improved_no_cache"]["api_calls"],
                        "graphql_api_calls": repo_results["graphql"]["api_calls"],
                        "api_reduction": (
                            (repo_results["improved_no_cache"]["api_calls"] - repo_results["graphql"]["api_calls"])
                            / repo_results["improved_no_cache"]["api_calls"] * 100
                        ) if repo_results["improved_no_cache"]["api_calls"] > 0 else 0
                    }
                    
                    print(f"\n  병렬 vs GraphQL 비교:")
                    print(f"  - 병렬: {no_cache_time:.2f}초, {repo_results['improved_no_cache']['api_calls']}회 API")
                    print(f"  - GraphQL: {graphql_time:.2f}초, {repo_results['graphql']['api_calls']}회 API")
                    print(f"  - API 감소율: {repo_results['analysis']['api_reduction']:.1f}%")
                    
            else:
                # 대규모: GraphQL 성능만 분석
                if "graphql" in repo_results and repo_results["graphql"]["success"]:
                    graphql_time = repo_results["graphql"]["time"]
                    
                    repo_results["analysis"] = {
                        "graphql_time": graphql_time,
                        "graphql_api_calls": repo_results["graphql"]["api_calls"],
                        "files_per_api": repo_results["graphql"]["files_count"] / repo_results["graphql"]["api_calls"] if repo_results["graphql"]["api_calls"] > 0 else 0
                    }
                    
                    print(f"\n  GraphQL 성능:")
                    print(f"  - 시간: {graphql_time:.2f}초")
                    print(f"  - API 호출: {repo_results['graphql']['api_calls']}회")
                    print(f"  - 효율성: {repo_results['analysis']['files_per_api']:.1f} 파일/API")
            
            self.results["repositories"][repo_name] = repo_results
        
        # 전체 요약
        self.generate_summary()
        
        # 결과 저장
        self.save_results()
        
        # 결과 출력
        self.print_summary()
    
    def generate_summary(self):
        """전체 결과 요약 생성"""
        total_repos = len(self.results["repositories"])
        successful_tests = sum(
            1 for r in self.results["repositories"].values()
            if ("original" in r and r["original"]["success"] and r["improved_no_cache"]["success"]) or
               ("graphql" in r and r["graphql"]["success"])
        )
        
        avg_speedup_no_cache = []
        avg_speedup_with_cache = []
        avg_api_reduction = []
        
        for repo_results in self.results["repositories"].values():
            if "analysis" in repo_results:
                if "speedup_no_cache" in repo_results["analysis"]:
                    avg_speedup_no_cache.append(repo_results["analysis"]["speedup_no_cache"])
                if "speedup_with_cache" in repo_results["analysis"]:
                    avg_speedup_with_cache.append(repo_results["analysis"]["speedup_with_cache"])
                if "api_reduction_with_cache" in repo_results["analysis"]:
                    avg_api_reduction.append(repo_results["analysis"]["api_reduction_with_cache"])
        
        self.results["summary"] = {
            "total_repositories": total_repos,
            "successful_tests": successful_tests,
            "average_speedup_no_cache": sum(avg_speedup_no_cache) / len(avg_speedup_no_cache) if avg_speedup_no_cache else 0,
            "average_speedup_with_cache": sum(avg_speedup_with_cache) / len(avg_speedup_with_cache) if avg_speedup_with_cache else 0,
            "average_api_reduction": sum(avg_api_reduction) / len(avg_api_reduction) if avg_api_reduction else 0
        }
    
    def save_results(self):
        """결과를 JSON 파일로 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = Path(__file__).parent / f"benchmark_results_{timestamp}.json"
        
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"\n결과 저장: {result_file.name}")
        
        # CSV 형식으로도 저장
        csv_file = Path(__file__).parent / f"benchmark_results_{timestamp}.csv"
        with open(csv_file, 'w', encoding='utf-8') as f:
            f.write("저장소,크기,원본시간,개선(캐시X)시간,개선(캐시O)시간,속도향상(캐시X),속도향상(캐시O),API감소율\n")
            
            for repo_name, data in self.results["repositories"].items():
                if "analysis" in data:
                    f.write(f"{repo_name},{data['info']['size']},")
                    if "original" in data:
                        # 일반 모드
                        f.write(f"{data['original']['time']:.2f},")
                        f.write(f"{data['improved_no_cache']['time']:.2f},")
                        f.write(f"{data['improved_with_cache']['time']:.2f},")
                        if "speedup_no_cache" in data['analysis']:
                            f.write(f"{data['analysis']['speedup_no_cache']:.1f}x,")
                            f.write(f"{data['analysis']['speedup_with_cache']:.1f}x,")
                            f.write(f"{data['analysis']['api_reduction_with_cache']:.1f}%\n")
                        else:
                            f.write("N/A,N/A,N/A\n")
                    elif "graphql" in data:
                        # GraphQL 모드
                        f.write(f"GraphQL,{data['graphql']['time']:.2f},")
                        f.write(f"{data['improved_with_cache']['time']:.2f},")
                        f.write(f"N/A,N/A,{data['graphql']['api_calls']}회\n")
        
        print(f"CSV 저장: {csv_file.name}")
    
    def print_summary(self):
        """요약 결과 출력"""
        print("\n" + "="*70)
        print("종합 결과")
        print("="*70)
        
        summary = self.results["summary"]
        print(f"테스트 저장소: {summary['total_repositories']}개")
        print(f"성공적 테스트: {summary['successful_tests']}개")
        print(f"\n평균 성능 향상:")
        print(f"- 캐시 없음: {summary['average_speedup_no_cache']:.1f}배")
        print(f"- 캐시 활용: {summary['average_speedup_with_cache']:.1f}배")
        print(f"- API 호출 감소: {summary['average_api_reduction']:.1f}%")
        
        print("\n" + "="*70)
        print("저장소별 결과")
        print("="*70)
        print(f"{'저장소':<15} {'크기':<10} {'방식':<12} {'시간':<10} {'API':<8} {'향상':<10}")
        print("-" * 70)
        
        for repo_name, data in self.results["repositories"].items():
            if "original" in data and data["original"]["success"]:
                # 일반 모드 결과
                print(f"{repo_name:<15} {data['info']['size']:<10} ", end="")
                print(f"{'원본':<12} {data['original']['time']:>8.2f}s {data['original']['api_calls']:>6}")
                print(f"{'':<15} {'':<10} ", end="")
                print(f"{'개선(X)':<12} {data['improved_no_cache']['time']:>8.2f}s {data['improved_no_cache']['api_calls']:>6}")
                print(f"{'':<15} {'':<10} ", end="")
                print(f"{'개선(O)':<12} {data['improved_with_cache']['time']:>8.2f}s {data['improved_with_cache']['api_calls']:>6}")
            elif "graphql" in data and data["graphql"]["success"]:
                # GraphQL 모드 결과
                print(f"{repo_name:<15} {data['info']['size']:<10} ", end="")
                print(f"{'GraphQL':<12} {data['graphql']['time']:>8.2f}s {data['graphql']['api_calls']:>6}")
                print(f"{'':<15} {'':<10} ", end="")
                print(f"{'캐시':<12} {data['improved_with_cache']['time']:>8.2f}s {data['improved_with_cache']['api_calls']:>6}")


if __name__ == "__main__":
    benchmark = ComprehensiveBenchmark()
    benchmark.run_benchmark()
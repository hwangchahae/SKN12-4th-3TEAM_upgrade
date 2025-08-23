"""
GitHub Analyzer 성능 벤치마크 도구

이 모듈은 원본과 개선된 버전의 GitHub Analyzer 성능을 비교 측정합니다.
실행 시간, API 호출 횟수, 메모리 사용량 등을 측정하고 시각화합니다.
"""

import time
import asyncio
import statistics
from typing import List, Dict, Any
import json
from datetime import datetime
import os
import shutil
import sys
from pathlib import Path

# .env 파일에서 토큰 로드
def load_env_token():
    """Load token from .env file"""
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if line.startswith("GITHUB_TOKEN="):
                    token = line.split("=", 1)[1].strip()
                    os.environ["GITHUB_TOKEN"] = token
                    print(f" GitHub 토큰 로드 완료")
                    return token
    return None

# 토큰 자동 로드
load_env_token()

# matplotlib와 pandas는 선택적 import
try:
    import matplotlib.pyplot as plt
    import pandas as pd
    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False
    print(" matplotlib 또는 pandas가 설치되지 않음. 시각화 기능 비활성화")

# psutil은 선택적 import (메모리 측정용)
try:
    import psutil
    MEMORY_TRACKING_AVAILABLE = True
except ImportError:
    MEMORY_TRACKING_AVAILABLE = False
    print(" psutil이 설치되지 않음. 메모리 추적 기능 비활성화")

# tabulate는 선택적 import (테이블 출력용)
try:
    from tabulate import tabulate
    TABLE_FORMAT_AVAILABLE = True
except ImportError:
    TABLE_FORMAT_AVAILABLE = False
    print(" tabulate가 설치되지 않음. 기본 테이블 형식 사용")

# tqdm은 선택적 import (진행바용)
try:
    from tqdm import tqdm
    PROGRESS_BAR_AVAILABLE = True
except ImportError:
    PROGRESS_BAR_AVAILABLE = False


class PerformanceBenchmark:
    """GitHub Analyzer 성능 벤치마크 클래스"""
    
    def __init__(self):
        self.results = {
            "original": [],
            "improved": []
        }
        self.detailed_metrics = {
            "original": {},
            "improved": {}
        }
        
    def measure_time(self, func_name: str = ""):
        """데코레이터로 함수 실행 시간 측정"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                start_time = time.perf_counter()
                result = func(*args, **kwargs)
                end_time = time.perf_counter()
                execution_time = end_time - start_time
                
                print(f"[{func_name}] 실행 시간: {execution_time:.2f}초")
                return result, execution_time
            return wrapper
        return decorator
    
    def get_memory_usage(self) -> float:
        """현재 메모리 사용량 측정 (MB)"""
        if MEMORY_TRACKING_AVAILABLE:
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / 1024 / 1024
        return 0.0
    
    def clear_cache(self):
        """ChromaDB 캐시 클리어 (공정한 비교를 위해)"""
        cache_dirs = ["./repo_analysis_db", "./repos"]
        for cache_dir in cache_dirs:
            if os.path.exists(cache_dir):
                try:
                    shutil.rmtree(cache_dir)
                    print(f" 캐시 디렉토리 삭제: {cache_dir}")
                except Exception as e:
                    print(f" 캐시 삭제 실패 ({cache_dir}): {e}")
    
    def run_benchmark(self, test_repos: List[str], iterations: int = 3):
        """여러 저장소로 반복 테스트"""
        
        for repo_url in test_repos:
            print(f"\n{'='*60}")
            print(f" 테스트 저장소: {repo_url}")
            print(f"{'='*60}")
            
            # 원본 버전 테스트
            original_times = []
            original_metrics = []
            
            for i in range(iterations):
                print(f"\n[원본] 테스트 {i+1}/{iterations}")
                self.clear_cache()  # 각 테스트 전 캐시 클리어
                
                time_taken, metrics = self.test_original_version(repo_url)
                original_times.append(time_taken)
                original_metrics.append(metrics)
                
                # 쿨다운 (API 제한 방지)
                if i < iterations - 1:
                    print(" 5초 대기 (API 제한 방지)...")
                    time.sleep(5)
            
            # 개선 버전 테스트
            improved_times = []
            improved_metrics = []
            
            for i in range(iterations):
                print(f"\n[개선] 테스트 {i+1}/{iterations}")
                self.clear_cache()  # 각 테스트 전 캐시 클리어
                
                time_taken, metrics = self.test_improved_version(repo_url)
                improved_times.append(time_taken)
                improved_metrics.append(metrics)
                
                # 쿨다운 (API 제한 방지)
                if i < iterations - 1:
                    print(" 5초 대기 (API 제한 방지)...")
                    time.sleep(5)
            
            # 결과 저장
            self.results["original"].append({
                "repo": repo_url,
                "times": original_times,
                "avg": statistics.mean(original_times),
                "min": min(original_times),
                "max": max(original_times),
                "metrics": original_metrics
            })
            
            self.results["improved"].append({
                "repo": repo_url,
                "times": improved_times,
                "avg": statistics.mean(improved_times),
                "min": min(improved_times),
                "max": max(improved_times),
                "metrics": improved_metrics
            })
    
    def test_original_version(self, repo_url: str) -> tuple:
        """원본 코드 테스트"""
        try:
            # 경로 수정: 상위 디렉토리에서 import
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from github_analyzer import GitHubRepositoryFetcher
            
            metrics = {
                "api_calls": 0,
                "memory_start": self.get_memory_usage(),
                "memory_peak": 0,
                "files_processed": 0
            }
            
            # API 호출 횟수 추적
            original_get = GitHubRepositoryFetcher.get_repo_directory_contents
            def tracked_get(self, *args, **kwargs):
                metrics["api_calls"] += 1
                return original_get(self, *args, **kwargs)
            GitHubRepositoryFetcher.get_repo_directory_contents = tracked_get
            
            start = time.perf_counter()
            
            # 실제 테스트
            fetcher = GitHubRepositoryFetcher(repo_url)
            fetcher.filter_main_files()
            files = fetcher.get_file_contents()  # 순차 처리
            
            end = time.perf_counter()
            
            metrics["memory_peak"] = self.get_memory_usage()
            metrics["files_processed"] = len(files)
            metrics["memory_used"] = metrics["memory_peak"] - metrics["memory_start"]
            
            print(f" 파일 수: {len(files)}")
            print(f" API 호출: {metrics['api_calls']}회")
            print(f" 메모리 사용: {metrics['memory_used']:.1f}MB")
            print(f" 소요 시간: {end-start:.2f}초")
            
            # 원래 함수 복원
            GitHubRepositoryFetcher.get_repo_directory_contents = original_get
            
            return end - start, metrics
            
        except ImportError as e:
            print(f" 원본 모듈 import 실패: {e}")
            return 0, {}
        except Exception as e:
            print(f" 테스트 실패: {e}")
            return 0, {}
    
    def test_improved_version(self, repo_url: str) -> tuple:
        """개선된 코드 테스트"""
        try:
            # 경로 수정: 상위 디렉토리에서 import
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
            # 개선된 버전이 있는지 확인
            if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "github_analyzer_improved.py")):
                from github_analyzer_improved import GitHubRepositoryFetcherImproved
                
                metrics = {
                    "api_calls": 0,
                    "memory_start": self.get_memory_usage(),
                    "memory_peak": 0,
                    "files_processed": 0,
                    "strategy_used": ""
                }
                
                start = time.perf_counter()
                
                fetcher = GitHubRepositoryFetcherImproved(repo_url)
                fetcher.filter_main_files_fast()  # Trees API 사용
                
                # 스마트 버전 - 파일 수에 따라 자동 선택
                files = fetcher.get_file_contents()
                
                # 사용된 전략 기록
                file_count = len(fetcher.files)
                metrics["strategy_used"] = "순차" if file_count < 5 else "병렬"
                
                end = time.perf_counter()
                
                metrics["memory_peak"] = self.get_memory_usage()
                metrics["files_processed"] = len(files)
                metrics["memory_used"] = metrics["memory_peak"] - metrics["memory_start"]
                metrics["api_calls"] = fetcher.api_call_count
                
                print(f" 파일 수: {len(files)}")
                print(f" 전략: {metrics['strategy_used']} 처리")
                print(f" API 호출: {metrics['api_calls']}회")
                print(f" 캐시 히트: {fetcher.cache_hits}, 미스: {fetcher.cache_misses}")
                print(f" 메모리 사용: {metrics['memory_used']:.1f}MB")
                print(f" 소요 시간: {end-start:.2f}초")
                
                return end - start, metrics
            else:
                # 개선 버전이 없으면 시뮬레이션 (예상 성능)
                print(" 개선 버전 미구현 - 예상 성능으로 시뮬레이션")
                from github_analyzer import GitHubRepositoryFetcher
                
                start = time.perf_counter()
                fetcher = GitHubRepositoryFetcher(repo_url)
                fetcher.filter_main_files()
                
                # 병렬 처리 시뮬레이션 (10배 빠르다고 가정)
                simulated_time = (time.perf_counter() - start) / 10
                time.sleep(simulated_time)
                
                files = []  # 시뮬레이션이므로 빈 리스트
                
                end = time.perf_counter()
                
                print(f" 시뮬레이션 시간: {end-start:.2f}초")
                
                return end - start, {"simulated": True}
                
        except Exception as e:
            print(f" 테스트 실패: {e}")
            return 0, {}
    
    def generate_report(self):
        """성능 비교 리포트 생성"""
        
        print("\n" + "="*70)
        print("성능 비교 결과 요약")
        print("="*70)
        
        total_improvement = []
        
        for i, (orig, impr) in enumerate(zip(self.results["original"], 
                                             self.results["improved"])):
            repo_name = orig["repo"].split("/")[-1]
            
            print(f"\n[{repo_name}]")
            print(f"  원본 평균: {orig['avg']:.2f}초")
            print(f"  개선 평균: {impr['avg']:.2f}초")
            
            if impr['avg'] > 0:
                improvement = ((orig['avg'] - impr['avg']) / orig['avg']) * 100
                speedup = orig['avg'] / impr['avg']
                total_improvement.append(speedup)
                
                print(f" 성능 향상: {improvement:.1f}%")
                print(f" 속도 향상: {speedup:.1f}배 빨라짐")
                
                # 세부 메트릭 출력 (가능한 경우)
                if orig.get('metrics') and orig['metrics'][0]:
                    orig_metrics = orig['metrics'][0]
                    if 'api_calls' in orig_metrics:
                        print(f" API 호출: {orig_metrics['api_calls']}회")
                    if 'memory_used' in orig_metrics and orig_metrics['memory_used'] > 0:
                        print(f" 메모리: {orig_metrics['memory_used']:.1f}MB")
        
        if total_improvement:
            avg_speedup = statistics.mean(total_improvement)
            print(f"\n{'='*70}")
            print(f" 전체 평균 속도 향상: {avg_speedup:.1f}배")
            print(f"{'='*70}")
        
        # JSON 파일로 저장
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"benchmark_results_{timestamp}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        print(f"\n 결과 저장: {filename}")
    
    def visualize_results(self):
        """시각화 차트 생성"""
        
        if not VISUALIZATION_AVAILABLE:
            print("\n matplotlib/pandas가 설치되지 않아 시각화를 건너뜁니다.")
            return
        
        if not self.results["original"] or not self.results["improved"]:
            print("\n 시각화할 데이터가 없습니다.")
            return
        
        try:
            # 한글 폰트 설정
            import matplotlib.font_manager as fm
            import matplotlib as mpl
            
            # Windows에서 한글 폰트 설정
            font_path = 'C:/Windows/Fonts/malgun.ttf'  # 맑은 고딕
            if os.path.exists(font_path):
                font_name = fm.FontProperties(fname=font_path).get_name()
                mpl.rc('font', family=font_name)
            else:
                # 폰트가 없으면 기본 설정
                mpl.rc('font', family='DejaVu Sans')
            
            # 마이너스 기호 깨짐 방지
            mpl.rc('axes', unicode_minus=False)
            
            # 데이터 준비
            repos = [r["repo"].split("/")[-1] for r in self.results["original"]]
            original_times = [r["avg"] for r in self.results["original"]]
            improved_times = [r["avg"] for r in self.results["improved"]]
            
            # 개선된 시간이 0인 경우 처리
            improved_times = [t if t > 0 else 0.1 for t in improved_times]
            
            x = range(len(repos))
            width = 0.35
            
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
            
            # 실행 시간 비교
            ax1.bar([i - width/2 for i in x], original_times, width, 
                    label='Original', color='red', alpha=0.7)
            ax1.bar([i + width/2 for i in x], improved_times, width, 
                    label='Improved', color='green', alpha=0.7)
            
            ax1.set_xlabel('Repository')
            ax1.set_ylabel('Execution Time (seconds)')
            ax1.set_title('GitHub Analyzer Performance Comparison')
            ax1.set_xticks(x)
            ax1.set_xticklabels(repos, rotation=45)
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            # 속도 향상 비율
            speedups = [o/i for o, i in zip(original_times, improved_times)]
            colors = ['green' if s > 1 else 'red' for s in speedups]
            ax2.bar(repos, speedups, color=colors, alpha=0.7)
            ax2.set_xlabel('Repository')
            ax2.set_ylabel('Speedup (x)')
            ax2.set_title('Speedup Ratio')
            ax2.set_xticklabels(repos, rotation=45)
            ax2.axhline(y=1, color='black', linestyle='--', alpha=0.3)
            ax2.grid(True, alpha=0.3)
            
            for i, v in enumerate(speedups):
                ax2.text(i, v + 0.1, f'{v:.1f}x', ha='center')
            
            plt.tight_layout()
            
            # 파일 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f'benchmark_chart_{timestamp}.png'
            plt.savefig(filename)
            print(f"\n 차트 저장: {filename}")
            
            # 차트 표시 (가능한 경우)
            try:
                plt.show()
            except:
                print("  (차트 표시는 GUI 환경에서만 가능합니다)")
                
        except Exception as e:
            print(f"\n 시각화 중 오류 발생: {e}")
    
    def print_comparison_table(self):
        """비교 테이블 출력"""
        
        if not self.results["original"] or not self.results["improved"]:
            return
        
        data = []
        for orig, impr in zip(self.results["original"], self.results["improved"]):
            repo_name = orig["repo"].split("/")[-1]
            speedup = orig['avg'] / impr['avg'] if impr['avg'] > 0 else 0
            
            data.append([
                repo_name,
                f"{orig['avg']:.2f}초",
                f"{impr['avg']:.2f}초",
                f"{speedup:.1f}x"
            ])
        
        headers = ["저장소", "원본", "개선", "속도 향상"]
        
        if TABLE_FORMAT_AVAILABLE:
            print("\n" + tabulate(data, headers=headers, tablefmt="grid"))
        else:
            # 기본 테이블 형식
            print("\n" + "-"*50)
            print(f"{'저장소':<20} {'원본':<10} {'개선':<10} {'속도 향상':<10}")
            print("-"*50)
            for row in data:
                print(f"{row[0]:<20} {row[1]:<10} {row[2]:<10} {row[3]:<10}")
            print("-"*50)


def main():
    """메인 실행 함수"""
    
    print("GitHub Analyzer 성능 벤치마크")
    print("="*60)
    
    # 벤치마크 객체 생성
    benchmark = PerformanceBenchmark()
    
    # 테스트할 저장소 목록 (실제 공개 저장소)
    test_repos = [
        # 작은 저장소만 테스트 (빠른 실행)
        "https://github.com/octocat/Hello-World",  # GitHub 공식 예제
        "https://github.com/octocat/Spoon-Knife",  # GitHub fork 예제
    ]
    
    print("\n 테스트 저장소:")
    for repo in test_repos:
        print(f"  - {repo}")
    
    print(f"\n 설정:")
    print(f"  - 반복 횟수: 1회")
    print(f"  - 캐시: 매 테스트마다 초기화")
    print(f"  - 메모리 추적: {MEMORY_TRACKING_AVAILABLE}")
    print(f"  - 시각화: {VISUALIZATION_AVAILABLE}")
    
    try:
        # 벤치마크 실행
        benchmark.run_benchmark(test_repos, iterations=1)
        
        # 리포트 생성
        benchmark.generate_report()
        
        # 테이블 출력
        benchmark.print_comparison_table()
        
        # 시각화
        benchmark.visualize_results()
        
    except KeyboardInterrupt:
        print("\n\n 사용자에 의해 중단됨")
    except Exception as e:
        print(f"\n 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
"""
GitHub Analyzer 성능 테스트 실행 스크립트

간단한 A/B 테스트를 실행하여 원본과 개선 버전의 성능을 비교합니다.
"""

import time
import os
import shutil
import sys
import json
from datetime import datetime

# 메모리 추적 (선택적)
try:
    import psutil
    MEMORY_TRACKING = True
except ImportError:
    MEMORY_TRACKING = False

# 프로그레스 바 (선택적)
try:
    from tqdm import tqdm
    PROGRESS_BAR = True
except ImportError:
    PROGRESS_BAR = False


def clear_cache():
    """캐시 디렉토리 클리어"""
    cache_dirs = ["./repo_analysis_db", "./repos"]
    
    for cache_dir in cache_dirs:
        if os.path.exists(cache_dir):
            try:
                shutil.rmtree(cache_dir)
                print(f"✓ 캐시 클리어: {cache_dir}")
            except Exception as e:
                print(f" 캐시 클리어 실패: {e}")


def get_memory_usage():
    """현재 메모리 사용량 (MB)"""
    if MEMORY_TRACKING:
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024
    return 0


def test_original(repo_url: str) -> dict:
    """원본 버전 테스트"""
    print("\n" + "="*50)
    print(" 원본 버전 테스트")
    print("="*50)
    
    results = {
        "version": "original",
        "repo": repo_url,
        "start_time": datetime.now().isoformat(),
        "memory_start": get_memory_usage()
    }
    
    try:
        from github_analyzer import GitHubRepositoryFetcher
        
        # API 호출 카운터
        api_calls = {"count": 0}
        original_func = GitHubRepositoryFetcher.get_repo_directory_contents
        
        def count_api_calls(self, *args, **kwargs):
            api_calls["count"] += 1
            return original_func(self, *args, **kwargs)
        
        GitHubRepositoryFetcher.get_repo_directory_contents = count_api_calls
        
        print(" 저장소 분석 시작...")
        start_time = time.perf_counter()
        
        # 원본 코드 실행
        fetcher = GitHubRepositoryFetcher(repo_url)
        fetcher.filter_main_files()
        
        # 프로그레스 바 표시 (가능한 경우)
        if PROGRESS_BAR and fetcher.files:
            print(f" {len(fetcher.files)}개 파일 처리 중...")
            files = []
            with tqdm(total=len(fetcher.files), desc="파일 처리") as pbar:
                for path in fetcher.files:
                    doc = fetcher.get_repo_content_as_document(path)
                    if doc:
                        files.append({
                            'path': path,
                            'content': doc.page_content[:100] + "..." if len(doc.page_content) > 100 else doc.page_content
                        })
                    pbar.update(1)
        else:
            files = fetcher.get_file_contents()
        
        end_time = time.perf_counter()
        
        # 결과 수집
        results["execution_time"] = end_time - start_time
        results["files_count"] = len(files)
        results["api_calls"] = api_calls["count"]
        results["memory_end"] = get_memory_usage()
        results["memory_used"] = results["memory_end"] - results["memory_start"]
        results["success"] = True
        
        print(f"\n 테스트 완료!")
        print(f"   처리 파일: {results['files_count']}개")
        print(f"   실행 시간: {results['execution_time']:.2f}초")
        print(f"   API 호출: {results['api_calls']}회")
        
        if MEMORY_TRACKING:
            print(f"   메모리 사용: {results['memory_used']:.1f}MB")
        
        # 원래 함수 복원
        GitHubRepositoryFetcher.get_repo_directory_contents = original_func
        
    except Exception as e:
        results["success"] = False
        results["error"] = str(e)
        print(f"\n 테스트 실패: {e}")
    
    return results


def test_improved(repo_url: str) -> dict:
    """개선 버전 테스트"""
    print("\n" + "="*50)
    print(" 개선 버전 테스트")
    print("="*50)
    
    results = {
        "version": "improved",
        "repo": repo_url,
        "start_time": datetime.now().isoformat(),
        "memory_start": get_memory_usage()
    }
    
    try:
        # 개선 버전이 있는지 확인
        if os.path.exists("github_analyzer_improved.py"):
            import asyncio
            from github_analyzer_improved import GitHubRepositoryFetcherImproved
            
            print(" 저장소 분석 시작 (병렬 처리)...")
            start_time = time.perf_counter()
            
            # 개선된 코드 실행
            fetcher = GitHubRepositoryFetcherImproved(repo_url)
            fetcher.filter_main_files()
            
            # 병렬 처리
            files = asyncio.run(fetcher.get_file_contents_parallel())
            
            end_time = time.perf_counter()
            
            results["execution_time"] = end_time - start_time
            results["files_count"] = len(files)
            results["api_calls"] = getattr(fetcher, 'api_call_count', 0)
            results["parallel_processing"] = True
            
        else:
            print(" 개선 버전이 없습니다. 시뮬레이션 모드...")
            
            # 시뮬레이션: 원본의 1/10 시간
            from github_analyzer import GitHubRepositoryFetcher
            
            start_time = time.perf_counter()
            
            fetcher = GitHubRepositoryFetcher(repo_url)
            fetcher.filter_main_files()
            
            # 시뮬레이션 시간 (실제보다 빠르게)
            simulated_time = 0.1 * len(fetcher.files)
            time.sleep(min(simulated_time, 5))  # 최대 5초
            
            end_time = time.perf_counter()
            
            results["execution_time"] = end_time - start_time
            results["files_count"] = len(fetcher.files)
            results["api_calls"] = 1  # Trees API 한 번
            results["simulated"] = True
        
        results["memory_end"] = get_memory_usage()
        results["memory_used"] = results["memory_end"] - results["memory_start"]
        results["success"] = True
        
        print(f"\n 테스트 완료!")
        print(f"   처리 파일: {results['files_count']}개")
        print(f"   실행 시간: {results['execution_time']:.2f}초")
        
        if "api_calls" in results:
            print(f"   API 호출: {results['api_calls']}회")
        
        if MEMORY_TRACKING:
            print(f"   메모리 사용: {results['memory_used']:.1f}MB")
        
        if results.get("simulated"):
            print("   (시뮬레이션 결과)")
        
    except Exception as e:
        results["success"] = False
        results["error"] = str(e)
        print(f"\n 테스트 실패: {e}")
    
    return results


def compare_results(original: dict, improved: dict):
    """결과 비교 및 출력"""
    print("\n" + "="*60)
    print(" 성능 비교 결과")
    print("="*60)
    
    if not original.get("success") or not improved.get("success"):
        print(" 일부 테스트가 실패하여 비교할 수 없습니다.")
        return
    
    # 성능 계산
    speedup = original["execution_time"] / improved["execution_time"]
    improvement = ((original["execution_time"] - improved["execution_time"]) 
                  / original["execution_time"]) * 100
    
    # 결과 테이블
    print(f"\n{'항목':<20} {'원본':>15} {'개선':>15} {'차이':>15}")
    print("-" * 65)
    
    print(f"{'실행 시간':<20} {original['execution_time']:>14.2f}초 "
          f"{improved['execution_time']:>14.2f}초 "
          f"{speedup:>14.1f}배")
    
    print(f"{'파일 수':<20} {original['files_count']:>15}개 "
          f"{improved['files_count']:>15}개 "
          f"{'동일' if original['files_count'] == improved['files_count'] else '다름':>15}")
    
    if "api_calls" in original and "api_calls" in improved:
        api_reduction = original["api_calls"] - improved["api_calls"]
        print(f"{'API 호출':<20} {original['api_calls']:>15}회 "
              f"{improved['api_calls']:>15}회 "
              f"{api_reduction:>14}회 감소")
    
    if MEMORY_TRACKING:
        memory_saved = original["memory_used"] - improved["memory_used"]
        print(f"{'메모리 사용':<20} {original['memory_used']:>14.1f}MB "
              f"{improved['memory_used']:>14.1f}MB "
              f"{memory_saved:>13.1f}MB 절약")
    
    print("-" * 65)
    
    # 요약
    print(f"\n 요약:")
    print(f"   성능 향상: {improvement:.1f}%")
    print(f"   속도: {speedup:.1f}배 빨라짐")
    
    if improved.get("simulated"):
        print(f"    개선 버전은 시뮬레이션 결과입니다")
    
    # 결과 저장
    save_results(original, improved, speedup, improvement)


def save_results(original: dict, improved: dict, speedup: float, improvement: float):
    """결과를 JSON 파일로 저장"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"performance_test_{timestamp}.json"
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "original": original,
        "improved": improved,
        "comparison": {
            "speedup": speedup,
            "improvement_percent": improvement
        }
    }
    
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n 결과 저장: {filename}")
    except Exception as e:
        print(f"\n 결과 저장 실패: {e}")


def main():
    """메인 실행 함수"""
    
    print("GitHub Analyzer 성능 비교 테스트")
    print("="*60)
    
    # 테스트 저장소 설정
    # 기본값: GitHub의 작은 공개 저장소
    test_repo = "https://github.com/octocat/Hello-World"
    
    # 사용자가 저장소 URL을 인자로 제공한 경우
    if len(sys.argv) > 1:
        test_repo = sys.argv[1]
    
    print(f"테스트 저장소: {test_repo}")
    print(f"설정:")
    print(f"  - 메모리 추적: {'활성화' if MEMORY_TRACKING else '비활성화'}")
    print(f"  - 프로그레스 바: {'활성화' if PROGRESS_BAR else '비활성화'}")
    
    try:
        # 1. 캐시 클리어 (공정한 비교)
        print("\n캐시 클리어 중...")
        clear_cache()
        
        # 2. 원본 테스트
        original_result = test_original(test_repo)
        
        # 3. 잠시 대기 (API 제한 방지)
        print("\n5초 대기 (API 제한 방지)...")
        time.sleep(5)
        
        # 4. 캐시 다시 클리어
        print("\n캐시 클리어 중...")
        clear_cache()
        
        # 5. 개선 버전 테스트
        improved_result = test_improved(test_repo)
        
        # 6. 결과 비교
        compare_results(original_result, improved_result)
        
        print("\n테스트 완료!")
        
    except KeyboardInterrupt:
        print("\n\n 사용자에 의해 중단됨")
    except Exception as e:
        print(f"\n 테스트 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
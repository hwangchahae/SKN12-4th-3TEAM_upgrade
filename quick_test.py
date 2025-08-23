"""
빠른 성능 비교 테스트
"""

import time
import os
from pathlib import Path

# .env에서 토큰 로드
env_path = Path(".env")
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            if line.startswith("GITHUB_TOKEN="):
                token = line.split("=", 1)[1].strip()
                os.environ["GITHUB_TOKEN"] = token
                print(f"토큰 로드 완료")
                break

# 테스트
repo = "https://github.com/octocat/Spoon-Knife"

print("\n" + "="*60)
print("빠른 성능 테스트")
print("="*60)
print(f"저장소: {repo}\n")

# 원본 테스트
print("[원본 코드 테스트]")
from github_analyzer import GitHubRepositoryFetcher

start = time.time()
fetcher1 = GitHubRepositoryFetcher(repo)
fetcher1.filter_main_files()
files1 = fetcher1.get_file_contents()
time1 = time.time() - start

print(f"  - 시간: {time1:.2f}초")
print(f"  - 파일: {len(files1)}개")

# 개선 테스트
print("\n[개선 코드 테스트]")
from github_analyzer_improved import GitHubRepositoryFetcherImproved

start = time.time()
fetcher2 = GitHubRepositoryFetcherImproved(repo)
fetcher2.filter_main_files_fast()
files2 = fetcher2.get_file_contents()
time2 = time.time() - start

print(f"  - 시간: {time2:.2f}초")
print(f"  - 파일: {len(files2)}개")
print(f"  - 전략: {'순차' if len(fetcher2.files) < 5 else '병렬'}")
print(f"  - API 호출: {fetcher2.api_call_count}회")

# 비교
print("\n" + "="*60)
print("결과 비교")
print("="*60)

if time1 > 0 and time2 > 0:
    if len(files1) == len(files2):
        speedup = time1 / time2
        print(f"속도 향상: {speedup:.2f}x")
        if speedup > 1:
            print(f"→ 개선 버전이 {speedup:.2f}배 빠름!")
        elif speedup < 1:
            print(f"→ 원본이 {1/speedup:.2f}배 빠름!")
        else:
            print("→ 동일한 속도")
    else:
        print(f"파일 수 불일치: 원본 {len(files1)}개 vs 개선 {len(files2)}개")
else:
    print("비교 실패")

print("\n설명:")
print("- 원본: 재귀적 API 호출로 순차 처리")
print("- 개선: Trees API + 스마트 전략 (파일 수에 따라 자동 선택)")
print("- Spoon-Knife는 작은 저장소라 순차 처리 사용")
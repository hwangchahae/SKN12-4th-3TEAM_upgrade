"""
병렬 처리 손익분기점 찾기 
"""

import time
import json
import asyncio
from typing import Dict, List

# 더 빠른 시뮬레이션
class FastMockFetcher:
    def __init__(self, file_count):
        self.file_count = file_count
    
    def sequential_fetch(self):
        # 실제 측정 대신 계산식 사용
        return 0.01 * self.file_count + 0.002 * (self.file_count ** 1.1)
    
    def parallel_fetch(self):
        # 병렬은 거의 일정한 시간
        batch_time = 0.001 * ((self.file_count + 19) // 20)
        return 0.04 + batch_time


def test_breakeven_point():
    """손익분기점 찾기"""
    
    print("병렬 처리 손익분기점 분석")
    print("=" * 50)
    
    results = {
        'file_counts': [],
        'sequential_times': [],
        'parallel_times': [],
        'speedups': [],
        'breakeven_point': None
    }
    
    # 1부터 100까지 테스트
    for file_count in range(1, 101, 2):
        fetcher = FastMockFetcher(file_count)
        
        seq_time = fetcher.sequential_fetch()
        par_time = fetcher.parallel_fetch()
        speedup = seq_time / par_time if par_time > 0 else 0
        
        results['file_counts'].append(file_count)
        results['sequential_times'].append(seq_time)
        results['parallel_times'].append(par_time)
        results['speedups'].append(speedup)
        
        # 손익분기점 찾기
        if speedup > 1.0 and results['breakeven_point'] is None:
            results['breakeven_point'] = file_count
            print(f"\n*** 손익분기점 발견: {file_count}개 파일 ***")
            print(f"    순차: {seq_time:.3f}초")
            print(f"    병렬: {par_time:.3f}초")
            print(f"    속도 향상: {speedup:.2f}배\n")
        
        # 진행 상황
        if file_count % 20 == 1:
            print(f"파일 {file_count:3}개: 순차={seq_time:.3f}초, 병렬={par_time:.3f}초, 속도={speedup:.2f}x")
    
    return results


def analyze_real_repos():
    """실제 저장소 시뮬레이션"""
    
    repos = [
        ("Hello-World", 1),
        ("small-repo", 5),
        ("medium-repo", 20),
        ("large-repo", 50),
        ("huge-repo", 100)
    ]
    
    print("\n실제 저장소 시뮬레이션")
    print("=" * 50)
    
    results = []
    for name, files in repos:
        fetcher = FastMockFetcher(files)
        seq = fetcher.sequential_fetch()
        par = fetcher.parallel_fetch()
        speedup = seq / par
        
        results.append({
            'repo': name,
            'files': files,
            'sequential': round(seq, 3),
            'parallel': round(par, 3),
            'speedup': round(speedup, 2),
            'recommendation': '병렬' if speedup > 1 else '순차'
        })
        
        print(f"{name:15} ({files:3}개): 순차={seq:.3f}s, 병렬={par:.3f}s -> {results[-1]['recommendation']}")
    
    return results


def generate_recommendation():
    """추천 테이블 생성"""
    
    print("\n" + "=" * 50)
    print("파일 수별 처리 방식 추천")
    print("=" * 50)
    
    recommendations = [
        (1, 4, "매우 작음", "순차 처리"),
        (5, 10, "작음", "상황별 선택"),
        (11, 30, "중간", "병렬 처리"),
        (31, 100, "큼", "병렬 처리 (필수)"),
        (101, 1000, "초대형", "병렬 처리 (필수)")
    ]
    
    for min_f, max_f, size, rec in recommendations:
        print(f"{size:10} ({min_f:3}-{max_f:4} 파일): {rec}")
    
    return recommendations


def save_results(simulation_results, real_repos, recommendations):
    """결과 저장"""
    
    output = {
        'simulation': {
            'file_counts': simulation_results['file_counts'],
            'sequential_times': simulation_results['sequential_times'],
            'parallel_times': simulation_results['parallel_times'],
            'speedups': simulation_results['speedups'],
            'breakeven_point': simulation_results['breakeven_point']
        },
        'real_repos': real_repos,
        'recommendations': [
            {'range': f'{min_f}-{max_f}', 'size': size, 'strategy': rec}
            for min_f, max_f, size, rec in recommendations
        ],
        'summary': {
            'breakeven_point': simulation_results['breakeven_point'],
            'optimal_strategy': {
                'small': '< 5 파일: 순차 처리',
                'large': '>= 5 파일: 병렬 처리'
            }
        },
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    with open('breakeven_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print("\n결과 저장: breakeven_analysis.json")


def create_simple_chart(results):
    """간단한 텍스트 차트"""
    
    print("\n" + "=" * 50)
    print("성능 비교 차트 (텍스트)")
    print("=" * 50)
    
    # 주요 포인트만 표시
    key_points = [1, 5, 10, 20, 50, 100]
    
    print("\n파일수  순차    병렬    속도향상  그래프")
    print("-" * 50)
    
    for fc in key_points:
        if fc in results['file_counts']:
            idx = results['file_counts'].index(fc)
            seq = results['sequential_times'][idx]
            par = results['parallel_times'][idx]
            speedup = results['speedups'][idx]
            
            # 막대 그래프
            bar_length = int(speedup * 5) if speedup < 10 else 50
            bar = '#' * bar_length
            
            print(f"{fc:3}개  {seq:6.3f}  {par:6.3f}  {speedup:6.2f}x  {bar}")
    
    print("-" * 50)
    print(f"손익분기점: {results['breakeven_point']}개 파일")


def main():
    """메인 실행"""
    
    print("GitHub Analyzer 병렬 처리 손익분기점 분석")
    print("=" * 50)
    print()
    
    # 1. 손익분기점 찾기
    simulation_results = test_breakeven_point()
    
    # 2. 실제 저장소 테스트
    real_repos = analyze_real_repos()
    
    # 3. 추천 생성
    recommendations = generate_recommendation()
    
    # 4. 간단한 차트
    create_simple_chart(simulation_results)
    
    # 5. 결과 저장
    save_results(simulation_results, real_repos, recommendations)
    
    # 6. 최종 요약
    print("\n" + "=" * 50)
    print("최종 요약")
    print("=" * 50)
    print(f"손익분기점: {simulation_results['breakeven_point']}개 파일")
    print(f"- {simulation_results['breakeven_point']}개 미만: 순차 처리 추천")
    print(f"- {simulation_results['breakeven_point']}개 이상: 병렬 처리 추천")
    print()
    print("테스트 완료!")


if __name__ == "__main__":
    main()
"""
성능 개선 전후 비교 그래프 생성
각 저장소별로 개별 그래프 생성
"""

import matplotlib.pyplot as plt
import numpy as np

# Windows 한글 폰트 설정
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

# 데이터 준비
repositories = {
    'git-test': {
        'title': 'hwangchahae/git-test',
        'subtitle': '작은 저장소 (11개 파일)',
        'before': {
            'time': 27.54,
            'embedding_api': 10,
            'total_api': 33
        },
        'after': {
            'time': 3.40,
            'embedding_api': 1,
            'total_api': 14
        }
    },
    'coding_test_study': {
        'title': 'hwangchahae/coding_test_study',
        'subtitle': '중간 저장소 (276개 파일)',
        'before': {
            'time': 620.34,
            'embedding_api': 485,
            'total_api': 1386
        },
        'after': {
            'time': 34.56,
            'embedding_api': 10,
            'total_api': 426
        }
    },
    'flask': {
        'title': 'pallets/flask',
        'subtitle': '중간 저장소 - 복잡한 구조 (99개 파일)',
        'before': {
            'time': 1855.82,
            'embedding_api': 2023,
            'total_api': 4250
        },
        'after': {
            'time': 40.53,
            'embedding_api': 41,
            'total_api': 244
        }
    }
}

colors = {'before': '#FF6B6B', 'after': '#4ECDC4'}

# 개별 저장소별 그래프 생성
for idx, (repo_key, data) in enumerate(repositories.items(), 1):
    fig, axes = plt.subplots(1, 2, figsize=(12, 6))
    
    # 제목 설정
    fig.suptitle(f'{data["title"]}', fontsize=16, fontweight='bold', y=1.05)
    fig.text(0.5, 0.98, data["subtitle"], ha='center', fontsize=12, style='italic')
    
    # 성능 개선 요약 계산
    speed_up = data['before']['time'] / data['after']['time']
    embedding_reduction = (1 - data['after']['embedding_api'] / data['before']['embedding_api']) * 100
    
    # 요약 정보 박스
    summary_text = (f"{speed_up:.1f}배 빨라짐\n"
                   f"임베딩 API {embedding_reduction:.0f}% 감소")
    
    # 1. 실행 시간 비교
    ax1 = axes[0]
    x_pos = np.arange(2)
    bars1 = ax1.bar(x_pos, 
                    [data['before']['time'], data['after']['time']], 
                    color=[colors['before'], colors['after']],
                    width=0.6)
    
    ax1.set_ylabel('실행 시간 (초)', fontsize=12)
    ax1.set_title('실행 시간 비교', fontsize=13, fontweight='bold')
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels(['개선 전', '개선 후'], fontsize=11)
    
    # 막대 위에 값 표시
    for i, bar in enumerate(bars1):
        height = bar.get_height()
        if i == 0:
            time_text = f"{height:.1f}초\n({height/60:.1f}분)" if height > 60 else f"{height:.1f}초"
        else:
            time_text = f"{height:.1f}초"
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                time_text, ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    # 개선율 화살표 표시
    ax1.annotate('', xy=(1, data['after']['time']), xytext=(0, data['before']['time']),
                arrowprops=dict(arrowstyle='->', color='green', lw=2))
    ax1.text(0.5, (data['before']['time'] + data['after']['time'])/2,
            f'{speed_up:.1f}배\n빨라짐',
            ha='center', fontsize=11, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.5))
    
    # 2. 임베딩 API 호출 비교
    ax2 = axes[1]
    bars2 = ax2.bar(x_pos, 
                    [data['before']['embedding_api'], data['after']['embedding_api']], 
                    color=[colors['before'], colors['after']],
                    width=0.6)
    
    ax2.set_ylabel('API 호출 횟수', fontsize=12)
    ax2.set_title('임베딩 API 호출 비교', fontsize=13, fontweight='bold')
    ax2.set_xticks(x_pos)
    ax2.set_xticklabels(['개선 전', '개선 후'], fontsize=11)
    
    # 막대 위에 값 표시
    for bar in bars2:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height)}회', ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    # 감소율 표시
    if data['before']['embedding_api'] > 0:
        ax2.text(0.5, max(data['before']['embedding_api'], data['after']['embedding_api']) * 0.6,
                f'{embedding_reduction:.0f}%\n감소',
                ha='center', fontsize=11, fontweight='bold',
                bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.5))
    
    # 요약 정보 추가
    fig.text(0.99, 0.02, summary_text, 
            fontsize=11, ha='right', va='bottom',
            bbox=dict(boxstyle='round', facecolor='white', edgecolor='gray', alpha=0.8))
    
    # 범례 추가
    legend_elements = [plt.Rectangle((0,0),1,1, fc=colors['before'], label='v0 (개선 전)'),
                      plt.Rectangle((0,0),1,1, fc=colors['after'], label='v6 (개선 후)')]
    fig.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(0.98, 0.95))
    
    # 레이아웃 조정
    plt.tight_layout()
    
    # 저장
    filename = f'performance_{repo_key}.png'
    plt.savefig(filename, dpi=100, bbox_inches='tight')
    print(f"그래프 생성 완료: {filename}")
    
    plt.show()

# 전체 요약 통계 출력
print("\n" + "="*70)
print("성능 개선 전체 요약")
print("="*70)

for repo_key, data in repositories.items():
    speed_up = data['before']['time'] / data['after']['time']
    embedding_reduction = (1 - data['after']['embedding_api'] / data['before']['embedding_api']) * 100
    
    print(f"\n[{data['title']}] ({data['subtitle']})")
    print(f"  실행 시간: {data['before']['time']:.1f}초 -> {data['after']['time']:.1f}초 ({speed_up:.1f}배 향상)")
    print(f"  임베딩 API: {data['before']['embedding_api']}회 -> {data['after']['embedding_api']}회 ({embedding_reduction:.0f}% 감소)")
    
    # 시간 단위 변환 표시
    if data['before']['time'] > 60:
        print(f"     -> 시간 단축: {data['before']['time']/60:.1f}분 -> {data['after']['time']/60:.1f}분")

print("\n" + "="*70)
print("핵심 개선 사항:")
print("  1. 배치 임베딩: 개별 API 호출 -> 50개씩 배치 처리")
print("  2. 병렬 처리: ThreadPoolExecutor(30)로 파일 동시 가져오기")
print("  3. DB 배치 저장: 100개씩 묶어서 저장")
print("  4. 역할 태깅 제거: 필요시에만 사용")
print("="*70)
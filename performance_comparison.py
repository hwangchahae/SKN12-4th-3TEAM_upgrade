"""
성능 개선 전후 비교 그래프 생성
각 저장소별로 개별 비교
"""

import matplotlib.pyplot as plt
import numpy as np

# Windows 한글 폰트 설정
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

# 데이터 준비
repositories = {
    'git-test (작은 저장소)': {
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
    'coding_test_study (중간 저장소)': {
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
    'flask (큰 저장소)': {
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

# 그래프 생성
fig, axes = plt.subplots(3, 3, figsize=(15, 12))
fig.suptitle('GitHub 저장소 분석 성능 개선 전후 비교', fontsize=16, fontweight='bold')

colors = {'before': '#FF6B6B', 'after': '#4ECDC4'}

for idx, (repo_name, data) in enumerate(repositories.items()):
    # 시간 비교
    ax1 = axes[idx, 0]
    bars1 = ax1.bar(['개선 전', '개선 후'], 
                    [data['before']['time'], data['after']['time']], 
                    color=[colors['before'], colors['after']])
    ax1.set_ylabel('시간 (초)', fontsize=10)
    ax1.set_title(f'{repo_name}\n실행 시간', fontsize=11, fontweight='bold')
    
    # 막대 위에 값 표시
    for bar in bars1:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}초', ha='center', va='bottom', fontsize=9)
    
    # 개선율 표시
    improvement = (data['before']['time'] - data['after']['time']) / data['before']['time'] * 100
    speed_up = data['before']['time'] / data['after']['time']
    ax1.text(0.5, max(data['before']['time'], data['after']['time']) * 0.5,
            f'▼ {improvement:.1f}%\n({speed_up:.1f}배 빨라짐)',
            transform=ax1.transData, ha='center', fontsize=9,
            bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.3))
    
    # 임베딩 API 호출 비교
    ax2 = axes[idx, 1]
    bars2 = ax2.bar(['개선 전', '개선 후'], 
                    [data['before']['embedding_api'], data['after']['embedding_api']], 
                    color=[colors['before'], colors['after']])
    ax2.set_ylabel('API 호출 횟수', fontsize=10)
    ax2.set_title(f'{repo_name}\n임베딩 API 호출', fontsize=11, fontweight='bold')
    
    # 막대 위에 값 표시
    for bar in bars2:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height)}회', ha='center', va='bottom', fontsize=9)
    
    # 감소율 표시
    if data['before']['embedding_api'] > 0:
        reduction = (data['before']['embedding_api'] - data['after']['embedding_api']) / data['before']['embedding_api'] * 100
        ax2.text(0.5, max(data['before']['embedding_api'], data['after']['embedding_api']) * 0.5,
                f'▼ {reduction:.1f}%',
                transform=ax2.transData, ha='center', fontsize=9,
                bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.3))
    
    # 전체 API 호출 비교
    ax3 = axes[idx, 2]
    bars3 = ax3.bar(['개선 전', '개선 후'], 
                    [data['before']['total_api'], data['after']['total_api']], 
                    color=[colors['before'], colors['after']])
    ax3.set_ylabel('API 호출 횟수', fontsize=10)
    ax3.set_title(f'{repo_name}\n전체 API 호출', fontsize=11, fontweight='bold')
    
    # 막대 위에 값 표시
    for bar in bars3:
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height)}회', ha='center', va='bottom', fontsize=9)
    
    # 감소율 표시
    reduction = (data['before']['total_api'] - data['after']['total_api']) / data['before']['total_api'] * 100
    ax3.text(0.5, max(data['before']['total_api'], data['after']['total_api']) * 0.5,
            f'▼ {reduction:.1f}%',
            transform=ax3.transData, ha='center', fontsize=9,
            bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.3))

# 레이아웃 조정
plt.tight_layout()

# 범례 추가
legend_elements = [plt.Rectangle((0,0),1,1, fc=colors['before'], label='개선 전'),
                  plt.Rectangle((0,0),1,1, fc=colors['after'], label='개선 후')]
fig.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(0.98, 0.98))

# 저장 및 표시
plt.savefig('performance_comparison_by_repo.png', dpi=100, bbox_inches='tight')
plt.show()

print("✅ 그래프 생성 완료: performance_comparison_by_repo.png")

# 요약 통계 출력
print("\n" + "="*60)
print("성능 개선 요약")
print("="*60)

for repo_name, data in repositories.items():
    print(f"\n📊 {repo_name}")
    print(f"  시간: {data['before']['time']:.1f}초 → {data['after']['time']:.1f}초 ({data['before']['time']/data['after']['time']:.1f}배 향상)")
    print(f"  임베딩 API: {data['before']['embedding_api']}회 → {data['after']['embedding_api']}회 ({(1-data['after']['embedding_api']/data['before']['embedding_api'])*100:.1f}% 감소)")
    print(f"  전체 API: {data['before']['total_api']}회 → {data['after']['total_api']}회 ({(1-data['after']['total_api']/data['before']['total_api'])*100:.1f}% 감소)")
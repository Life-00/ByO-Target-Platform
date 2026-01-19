"""
Advanced Search Agent - Enhanced Filtering and Selection
추가된 기능:
1. Adaptive cutoff (엘보우/갭 방법으로 K 자동 결정)
2. 다양성 선택 (MMR - Maximal Marginal Relevance)  
3. 신뢰성 게이트 (실험 조건/수치 명시 여부, preprint 감지)
4. 3축 평가 (관련성, 다양성, 신뢰성)
"""

import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re
from datetime import datetime, timedelta

class AdvancedPaperFilter:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        
    def find_adaptive_cutoff(self, scores: List[float]) -> Tuple[float, int]:
        """
        엘보우 방법으로 최적 cutoff 찾기
        Returns: (cutoff_score, selected_count)
        """
        if len(scores) < 3:
            return 0.7, len(scores)
            
        # Sort scores in descending order
        sorted_scores = sorted(scores, reverse=True)
        
        # Calculate gaps between consecutive scores
        gaps = [sorted_scores[i] - sorted_scores[i+1] for i in range(len(sorted_scores)-1)]
        
        if not gaps:
            return sorted_scores[0] * 0.8, 1
            
        # Find the largest gap (elbow point)
        max_gap_idx = np.argmax(gaps)
        
        # Cutoff is the score after the largest gap
        cutoff_score = sorted_scores[max_gap_idx + 1]
        selected_count = max_gap_idx + 1
        
        # Ensure minimum quality threshold
        min_threshold = 0.6
        if cutoff_score < min_threshold:
            cutoff_score = min_threshold
            selected_count = sum(1 for score in sorted_scores if score >= min_threshold)
            
        return cutoff_score, min(selected_count, 10)  # Cap at 10
    
    def calculate_mmr_selection(self, papers: List[Dict], lambda_param: float = 0.7) -> List[Dict]:
        """
        MMR (Maximal Marginal Relevance) 다양성 선택
        lambda_param: 관련성 vs 다양성 균형 (1.0=관련성만, 0.0=다양성만)
        """
        if len(papers) <= 1:
            return papers
            
        # Extract text for similarity calculation
        texts = [f"{paper['title']} {paper['abstract'][:500]}" for paper in papers]
        
        try:
            # Calculate TF-IDF vectors
            tfidf_matrix = self.vectorizer.fit_transform(texts)
            similarity_matrix = cosine_similarity(tfidf_matrix)
        except:
            # Fallback: just return by relevance
            return sorted(papers, key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        selected = []
        remaining = list(range(len(papers)))
        
        # Select first paper (highest relevance)
        best_idx = max(remaining, key=lambda i: papers[i].get('relevance_score', 0))
        selected.append(best_idx)
        remaining.remove(best_idx)
        
        # Iteratively select diverse papers
        while remaining and len(selected) < min(8, len(papers)):
            mmr_scores = []
            
            for i in remaining:
                # Relevance component
                relevance = papers[i].get('relevance_score', 0)
                
                # Diversity component (negative similarity to selected papers)
                max_similarity = max(similarity_matrix[i][j] for j in selected)
                diversity = 1 - max_similarity
                
                # MMR score
                mmr_score = lambda_param * relevance + (1 - lambda_param) * diversity
                mmr_scores.append((mmr_score, i))
            
            # Select paper with highest MMR score
            _, best_idx = max(mmr_scores)
            selected.append(best_idx)
            remaining.remove(best_idx)
        
        return [papers[i] for i in selected]
    
    def assess_reliability(self, paper: Dict) -> Dict[str, Any]:
        """
        신뢰성 평가 게이트
        Returns: {"reliability_score": float, "flags": [], "metadata": {}}
        """
        title = paper.get('title', '')
        abstract = paper.get('abstract', '')
        text = f"{title} {abstract}".lower()
        
        reliability_score = 0.5  # Base score
        flags = []
        metadata = {}
        
        # 1. 실험 조건/수치 존재 여부
        experimental_indicators = [
            r'\d+\s*(mg/kg|μm|nm|mm|cm)', # 용량/농도
            r'n\s*=\s*\d+',                # 샘플 수
            r'p\s*[<>=]\s*0\.\d+',         # p-value
            r'\d+\s*(days?|hours?|weeks?)', # 시간
            r'(ic50|ec50|ld50)',           # IC50 등
            r'(control|treatment|placebo)', # 실험 디자인
        ]
        
        numeric_evidence = sum(1 for pattern in experimental_indicators 
                             if re.search(pattern, text))
        
        if numeric_evidence >= 3:
            reliability_score += 0.3
            metadata['experimental_evidence'] = 'high'
        elif numeric_evidence >= 1:
            reliability_score += 0.1
            metadata['experimental_evidence'] = 'medium'
        else:
            flags.append('limited_experimental_data')
            metadata['experimental_evidence'] = 'low'
        
        # 2. Preprint 감지
        if re.search(r'(preprint|biorxiv|medrxiv|arxiv)', text):
            reliability_score -= 0.2
            flags.append('preprint')
            metadata['publication_status'] = 'preprint'
        else:
            metadata['publication_status'] = 'peer_reviewed'
        
        # 3. Review paper 감지 (일반적으로 더 신뢰도 높음)
        if re.search(r'(review|systematic|meta-analysis)', text):
            reliability_score += 0.2
            metadata['paper_type'] = 'review'
        
        # 4. 방법론 명시 여부
        method_keywords = [
            'western blot', 'pcr', 'elisa', 'immunofluorescence',
            'rna-seq', 'microarray', 'qrt-pcr', 'flow cytometry'
        ]
        
        methods_found = [method for method in method_keywords if method in text]
        if methods_found:
            reliability_score += min(0.2, len(methods_found) * 0.05)
            metadata['methods_identified'] = methods_found
        
        # 5. 발표 날짜 기반 평가
        try:
            pub_date = paper.get('published_date', '')
            if pub_date:
                # 너무 오래된 논문 (5년 이상)은 약간 감점
                pub_year = int(pub_date[:4])
                current_year = datetime.now().year
                if current_year - pub_year > 5:
                    reliability_score -= 0.1
                    flags.append('older_publication')
        except:
            pass
        
        # Score normalization
        reliability_score = max(0.0, min(1.0, reliability_score))
        
        return {
            'reliability_score': reliability_score,
            'flags': flags,
            'metadata': metadata
        }
    
    def calculate_diversity_score(self, paper: Dict, selected_papers: List[Dict]) -> float:
        """
        기선택 논문들 대비 다양성 점수 계산
        """
        if not selected_papers:
            return 1.0
            
        current_text = f"{paper['title']} {paper['abstract'][:500]}"
        selected_texts = [f"{p['title']} {p['abstract'][:500]}" for p in selected_papers]
        
        try:
            all_texts = [current_text] + selected_texts
            tfidf_matrix = self.vectorizer.fit_transform(all_texts)
            similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()
            
            # Diversity = 1 - max_similarity
            max_similarity = np.max(similarities) if len(similarities) > 0 else 0
            return 1.0 - max_similarity
            
        except:
            return 0.5  # Fallback
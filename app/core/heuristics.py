"""Text quality heuristics and cleanup functions.

This module provides utilities to assess text extraction quality
and apply basic cleanup to improve readability.
"""

import re


def should_fallback_to_ocr(text: str) -> bool:
    """Determine if text extraction quality is too poor and OCR is needed.
    
    Checks for:
    - Very short text (< 40 chars likely means extraction failed)
    - High ratio of non-alphanumeric characters (garbled extraction)
    - Many isolated single letters (wrong column ordering)
    
    Args:
        text: Extracted text to evaluate
        
    Returns:
        True if OCR should be used instead, False if text is acceptable
    """
    text = text.strip()
    
    # Empty or very short text
    if len(text) < 40:
        return True
    
    # Count alphanumeric vs total characters
    alphanum_count = sum(c.isalnum() for c in text)
    total_count = len(text)
    
    if total_count == 0:
        return True
    
    alphanum_ratio = alphanum_count / total_count
    
    # If less than 65% alphanumeric, likely garbled
    if alphanum_ratio < 0.65:
        return True
    
    # Count isolated single letters (potential column ordering issue)
    # Pattern: word boundary, single letter, word boundary
    isolated_letters = len(re.findall(r'\b[a-zA-Z]\b', text))
    words = len(text.split())
    
    if words > 0 and isolated_letters / words > 0.3:
        return True
    
    return False


def cleanup_text(text: str) -> str:
    """Apply basic text cleanup heuristics.
    
    Operations:
    - Fix hyphenation at line breaks (word-\\nnext → wordnext)
    - Join lines that should be part of same paragraph
    - Normalize whitespace (collapse multiple newlines)
    - Preserve intentional paragraph breaks
    
    Args:
        text: Raw extracted text
        
    Returns:
        Cleaned text
    """
    # Fix hyphenation: word-\n followed by word continues → remove hyphen and newline
    # Match: letter(s), hyphen, newline, letter(s)
    text = re.sub(r'([a-zA-Z])-\s*\n\s*([a-zA-Z])', r'\1\2', text)
    
    # Join lines within paragraphs
    # If a line doesn't end with sentence-ending punctuation and
    # the next line starts with lowercase, join them
    lines = text.split('\n')
    cleaned_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i].rstrip()
        
        # Check if this line should be joined with next
        if i + 1 < len(lines):
            next_line = lines[i + 1].lstrip()
            
            # Join if:
            # - Current line doesn't end with sentence punctuation
            # - Next line starts with lowercase letter
            # - Both lines have content
            if (line and next_line and
                not line[-1] in '.!?:"' and
                next_line[0].islower()):
                # Join with space
                line = line + ' ' + next_line
                i += 2  # Skip next line since we merged it
            else:
                cleaned_lines.append(line)
                i += 1
        else:
            cleaned_lines.append(line)
            i += 1
    
    text = '\n'.join(cleaned_lines)
    
    # Normalize whitespace
    # Collapse 3+ consecutive newlines to 2 (preserve paragraph breaks)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Remove trailing whitespace from each line
    lines = text.split('\n')
    text = '\n'.join(line.rstrip() for line in lines)
    
    # Trim leading/trailing whitespace from entire text
    text = text.strip()
    
    return text


def calculate_quality_score(text: str) -> float:
    """Calculate a quality score for extracted text (0.0 to 1.0).
    
    Higher scores indicate better quality extraction.
    
    Args:
        text: Extracted text to evaluate
        
    Returns:
        Quality score from 0.0 (worst) to 1.0 (best)
    """
    if not text or len(text.strip()) == 0:
        return 0.0
    
    text = text.strip()
    score = 1.0
    
    # Penalty for very short text
    if len(text) < 40:
        score *= 0.3
    elif len(text) < 100:
        score *= 0.6
    
    # Check alphanumeric ratio
    alphanum_count = sum(c.isalnum() or c.isspace() for c in text)
    total_count = len(text)
    alphanum_ratio = alphanum_count / total_count
    
    # Good text should be mostly alphanumeric + spaces
    if alphanum_ratio < 0.5:
        score *= 0.3
    elif alphanum_ratio < 0.7:
        score *= 0.6
    elif alphanum_ratio < 0.85:
        score *= 0.9
    
    # Check for isolated letters
    isolated_letters = len(re.findall(r'\b[a-zA-Z]\b', text))
    words = len(text.split())
    
    if words > 0:
        isolated_ratio = isolated_letters / words
        if isolated_ratio > 0.3:
            score *= 0.4
        elif isolated_ratio > 0.15:
            score *= 0.7
    
    return min(max(score, 0.0), 1.0)


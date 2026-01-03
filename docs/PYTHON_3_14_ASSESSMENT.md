# Python 3.14 Support Assessment

**Status**: Under Investigation  
**Date**: January 3, 2026  
**Issue**: Assess the possibility of supporting Python 3.14

---

## Executive Summary

This document assesses the feasibility of adding Python 3.14 support to the Jenkins AI Chatbot Plugin. Based on the current dependency ecosystem, **Python 3.14 support is not immediately feasible** but should be monitored for future updates.

---

## Current Status

### Supported Python Versions
- ✅ Python 3.11
- ✅ Python 3.12
- ✅ Python 3.13

### Blocked Python Versions
- ❌ Python 3.14+

---

## Dependency Analysis

### Critical Blockers

The following dependencies are **critical blockers** for Python 3.14 support:

#### 1. **NumPy** (v2.2.6)
- **Status**: Limited Python 3.14 wheel availability
- **Impact**: HIGH - Core dependency for all ML/AI libraries
- **Used by**: PyTorch, transformers, sentence-transformers, scikit-learn, pandas, faiss
- **Tracking**: https://github.com/numpy/numpy/milestone/
- **Notes**: NumPy 2.x series has experimental Python 3.14 support, but binary wheels may not be available on PyPI for all platforms yet

#### 2. **PyTorch** (v2.7.1)
- **Status**: No official Python 3.14 wheels
- **Impact**: HIGH - Core ML framework
- **Used by**: sentence-transformers, transformers
- **Tracking**: https://github.com/pytorch/pytorch/issues
- **Notes**: PyTorch typically lags 3-6 months behind new Python releases for official wheel support

#### 3. **Numba** (v0.63.1) + llvmlite (v0.46.0)
- **Status**: No Python 3.14 support
- **Impact**: MEDIUM - Required for BM25 retrieval (vendored retriv package)
- **Tracking**: https://github.com/numba/numba/issues
- **Notes**: Numba requires LLVM bindings which need to be rebuilt for each Python version

#### 4. **Transformers** (v4.54.1)
- **Status**: Likely compatible, but depends on PyTorch
- **Impact**: HIGH - Core NLP library
- **Dependencies**: torch, numpy, tokenizers
- **Notes**: Library itself may be compatible, but runtime requires PyTorch

#### 5. **Sentence-Transformers** (v4.1.0)
- **Status**: Likely compatible, but depends on PyTorch
- **Impact**: HIGH - Used for embeddings
- **Dependencies**: torch, transformers, numpy
- **Notes**: Library itself may be compatible, but runtime requires PyTorch

### Potentially Compatible Dependencies

These dependencies may already support Python 3.14:

- ✅ FastAPI (v0.115.12)
- ✅ Pydantic (v2.12.5)
- ✅ Uvicorn (v0.34.3)
- ✅ LangChain ecosystem (v0.3.x)
- ✅ SQLAlchemy (v2.0.41)
- ✅ Requests, httpx, etc. (pure Python or stable C extensions)

---

## Testing Strategy

### Phase 1: Dependency Check (Manual)

1. **Check PyPI for Python 3.14 wheels**:
   ```bash
   # Check if wheels are available for critical packages
   pip download --only-binary=:all: --python-version 3.14 numpy torch numba
   ```

2. **Check dependency compatibility tables**:
   - NumPy: https://numpy.org/doc/stable/release.html
   - PyTorch: https://pytorch.org/get-started/locally/
   - Numba: https://numba.readthedocs.io/en/stable/user/installing.html

### Phase 2: Virtual Environment Test

1. **Create Python 3.14 test environment**:
   ```bash
   python3.14 -m venv venv-py314-test
   source venv-py314-test/bin/activate
   pip install --upgrade pip setuptools wheel
   ```

2. **Attempt dependency installation**:
   ```bash
   pip install -r requirements-cpu.txt
   ```

3. **Document errors**:
   - Record which packages fail
   - Note specific error messages
   - Identify if it's a build issue or wheel unavailability

### Phase 3: Backend Testing (If Phase 2 succeeds)

1. **Import test**:
   ```bash
   python3.14 -c "import torch; import numpy; import transformers; import sentence_transformers"
   ```

2. **API startup test**:
   ```bash
   PYTHONPATH=$(pwd) python3.14 -m uvicorn api.main:app --host 0.0.0.0 --port 8000
   ```

3. **Unit tests**:
   ```bash
   PYTHONPATH=$(pwd) python3.14 -m pytest tests/unit
   ```

---

## Workaround Options

### Option 1: Wait for Upstream Support ⏳
**Recommended**: Wait for PyTorch, NumPy, and Numba to release Python 3.14 wheels.

**Timeline**: Estimated 3-6 months after Python 3.14 official release

**Pros**:
- No code changes required
- Most stable and maintainable solution
- Official support from upstream

**Cons**:
- Passive waiting period
- No control over timeline

---

### Option 2: Build from Source 🔨
Install dependencies from source instead of wheels.

**Implementation**:
```bash
# Install build dependencies
sudo apt install -y python3.14-dev build-essential cmake

# Build NumPy from source
pip install numpy --no-binary :all:

# Build PyTorch from source (WARNING: takes hours)
pip install torch --no-binary :all:
```

**Pros**:
- May enable Python 3.14 support earlier

**Cons**:
- Very long build times (PyTorch: 1-4 hours)
- Requires significant disk space (>10GB)
- May fail on Windows without MSVC
- Not reproducible for end users
- CI/CD pipelines will be extremely slow

**Verdict**: ❌ Not recommended for production use

---

### Option 3: Replace BM25 Dependency (Partial Solution) 🔄
Replace `retriv` (which requires `numba`) with an alternative BM25 implementation.

**Candidates**:
- `rank-bm25` (pure Python, no numba dependency)
- `bm25s` (newer, lighter alternative)

**Implementation**:
```bash
# requirements-cpu.txt
- retriv @ git+https://github.com/giovanni-vaccarino/retriv.git@remove-pystemmer
+ rank-bm25==0.2.2
```

**Pros**:
- Removes Numba dependency
- May enable Python 3.14 support sooner
- Simpler dependency tree

**Cons**:
- Code changes required in BM25 retrieval logic
- Potential performance differences
- Still blocked by PyTorch/NumPy

**Verdict**: ⚠️ Partial solution only; doesn't solve PyTorch/NumPy blocker

---

### Option 4: Conditional Python 3.14 Support (Graceful Degradation) 🎚️
Allow Python 3.14, but disable features that require incompatible dependencies.

**Implementation**:
```python
# chatbot-core/api/config/loader.py
import sys

PYTHON_VERSION = sys.version_info[:2]

if PYTHON_VERSION >= (3, 14):
    logger.warning("Python 3.14+ detected. Some features may be unavailable.")
    NUMBA_AVAILABLE = False
    BM25_AVAILABLE = False
```

**Pros**:
- Allows early adopters to test
- Progressive enhancement strategy

**Cons**:
- Degraded functionality
- Complex conditional logic
- User confusion about missing features

**Verdict**: ❌ Not recommended; breaks core functionality

---

## Recommendation

### Short-term (Now - Q2 2026)
1. ✅ **Document current limitation** (already done in setup.md)
2. ✅ **Monitor upstream progress** on NumPy, PyTorch, Numba
3. ✅ **Keep Python 3.11-3.13 as supported versions**
4. ⏳ **Retest quarterly** as new dependency versions are released

### Medium-term (Q2-Q4 2026)
1. 🔄 **Test Python 3.14 compatibility** once PyTorch releases wheels
2. 🔄 **Update CI/CD** to test against Python 3.14
3. 🔄 **Update documentation** to add Python 3.14 to supported versions

### Long-term (2027+)
1. 🎯 **Drop Python 3.11 support** (following Python's support lifecycle)
2. 🎯 **Support Python 3.14-3.16**

---

## Action Items

- [ ] **Monitor**: Subscribe to release notifications for NumPy, PyTorch, Numba
- [ ] **Test**: Set up automated quarterly testing for Python 3.14 compatibility
- [ ] **Document**: Keep this assessment up to date as ecosystem evolves
- [ ] **CI**: Add Python 3.14 to test matrix once dependencies are ready (expected Q2-Q3 2026)

---

## References

### Official Python 3.14 Release
- Release date: October 2025 (estimated)
- EOL: October 2030 (estimated)
- https://peps.python.org/pep-0745/

### Dependency Tracking
- NumPy: https://github.com/numpy/numpy/releases
- PyTorch: https://github.com/pytorch/pytorch/releases
- Numba: https://github.com/numba/numba/releases
- Python compatibility: https://devguide.python.org/versions/

### Community Discussion
- Scientific Python SPEC 0: https://scientific-python.org/specs/spec-0000/
  - Recommends supporting Python versions released in the last 42 months
  - Python 3.11+ currently recommended (as of 2026)

---

## Conclusion

**Python 3.14 support is currently blocked by the PyTorch/NumPy/Numba ecosystem.**

The recommended approach is to:
1. **Wait** for upstream dependencies to release Python 3.14 wheels (estimated Q2-Q3 2026)
2. **Monitor** progress on dependency trackers
3. **Test** quarterly to catch the transition point
4. **Update** documentation and CI when ready

No immediate action is required beyond monitoring the ecosystem. The current supported versions (Python 3.11-3.13) align with industry best practices and provide excellent stability.

#pragma once

#include <qlat-utils/config.h>
#include <qlat-utils/handle.h>
#include <qlat-utils/utils.h>
#include <unistd.h>

#include <cstdlib>
#include <cstring>
#include <unordered_map>

#ifdef QLAT_USE_MALLOC_STATS
#include <malloc.h>
#endif

namespace qlat
{  //

void clear_mem_cache();

void clear_all_caches();

// --------------------

enum struct MemType : Int {
  Cpu,   // CPU main memory
  Acc,   // Accelerator
  Comm,  // For communication on CPU
  Uvm,   // Uniform virtual memory
  SIZE,
};

std::string show(const MemType mem_type);

MemType read_mem_type(const std::string& mem_type_str);

API inline MemType& get_default_mem_type()
{
  static MemType mem_type =
      read_mem_type(get_env_default("q_default_mem_type", "uvm"));
  return mem_type;
}

inline bool is_same_mem_type(const MemType t1, const MemType t2)
{
  if (t1 == t2) {
    return true;
  } else {
#ifdef QLAT_USE_ACC
    return false;
#else
    if (t1 == MemType::Comm or t2 == MemType::Comm) {
      return false;
    } else {
      return true;
    }
#endif
  }
}

API inline Long& get_alignment()
// qlat parameter
//
// Should NOT change in the middle of the run.
{
  static Long alignment = 256;
  return alignment;
}

inline Long get_aligned_mem_size(const Long alignment, const Long min_size)
{
  const Long n_elem = 1 + (min_size - 1) / alignment;
  const Long size = n_elem * alignment;
  return size;
}

API inline Long& get_mem_cache_max_size(const MemType mem_type)
// qlat parameter
// unit in MB
{
  static Long max_size = get_env_long_default("q_mem_cache_max_size", 512);
  static Long max_size_cpu =
      get_env_long_default("q_mem_cache_cpu_max_size", max_size) * 1024L *
      1024L;
  static Long max_size_acc =
      get_env_long_default("q_mem_cache_acc_max_size", max_size) * 1024L *
      1024L;
  static Long max_size_comm =
      get_env_long_default("q_mem_cache_comm_max_size", max_size) * 1024L *
      1024L;
  static Long max_size_uvm =
      get_env_long_default("q_mem_cache_uvm_max_size", max_size) * 1024L *
      1024L;
  if (mem_type == MemType::Cpu) {
    return max_size_cpu;
  } else if (mem_type == MemType::Acc) {
    return max_size_acc;
  } else if (mem_type == MemType::Comm) {
    return max_size_comm;
  } else if (mem_type == MemType::Uvm) {
    return max_size_uvm;
  } else {
    qassert(false);
    return max_size;
  }
}

API inline Long& get_alloc_mem_max_size()
// qlat parameter
// unit in MB
{
  static Long max_size =
      get_env_long_default("q_alloc_mem_max_size", 256L * 1024L) * 1024L *
      1024L;
  return max_size;
}

struct MemoryStats {
  Long alloc[static_cast<Int>(MemType::SIZE)];
  Long cache[static_cast<Int>(MemType::SIZE)];
  //
  MemoryStats() { init(); }
  //
  void init()
  {
    for (Int i = 0; i < static_cast<Int>(MemType::SIZE); ++i) {
      alloc[i] = 0;
      cache[i] = 0;
    }
  }
  //
  Long total()
  // total memory include the size of the cache
  {
    Long total = 0;
    for (Int i = 0; i < static_cast<Int>(MemType::SIZE); ++i) {
      total += alloc[i] + cache[i];
    }
    return total;
  }
};

API inline MemoryStats& get_mem_stats()
{
  static MemoryStats ms;
  return ms;
}

void* alloc_mem_alloc(const Long size, const MemType mem_type);

void free_mem_free(void* ptr, const Long size, const MemType mem_type);

struct API MemCache {
  MemType mem_type;
  Long mem_cache_max_size;
  Long mem_cache_size;
  std::unordered_multimap<Long, void*> db;
  //
  MemCache(const MemType mem_type_ = get_default_mem_type(),
           const Long mem_cache_max_size_ = -1)
  {
    init(mem_type_, mem_cache_max_size_);
  }
  ~MemCache() { gc(); }
  //
  void init(const MemType mem_type_ = get_default_mem_type(),
            const Long mem_cache_max_size_ = -1);
  void add(void* ptr, const Long size);
  void* del(const Long size);
  void gc();
};

std::vector<MemCache> mk_mem_cache_vec();

API inline MemCache& get_mem_cache(
    const MemType mem_type = get_default_mem_type())
{
  static std::vector<MemCache> cache_vec = mk_mem_cache_vec();
  return cache_vec[static_cast<Int>(mem_type)];
}

void* alloc_mem(const Long min_size, const MemType mem_type);

void free_mem(void* ptr, const Long min_size, const MemType mem_type);

void copy_mem(void* dst, const MemType mem_type_dst, const void* src,
              const MemType mem_type_src, const Long size);

// --------------------

inline void displayln_malloc_stats()
{
#ifdef QLAT_USE_MALLOC_STATS
  malloc_stats();
#endif
}

// --------------------

template <class M>
struct API vector {
  // Avoid copy constructor when possible
  // (it is likely not what you think it is)
  // Only used in qacc macros, or if it is already a copy.
  //
  Vector<M> v;
  MemType mem_type;  // if place data on accelerator memory
  bool is_copy;      // do not free memory if is_copy=true
  //
  vector(const MemType mem_type_ = get_default_mem_type())
  {
    qassert(v.p == NULL);
    mem_type = mem_type_;
    is_copy = false;
  }
  vector(const Long size, const MemType mem_type_ = get_default_mem_type())
  {
    // TIMER("vector::vector(size)")
    qassert(v.p == NULL);
    mem_type = mem_type_;
    is_copy = false;
    resize(size);
  }
  vector(const std::vector<M>& vp, const MemType mem_type_ = get_default_mem_type())
  {
    // TIMER("vector::vector(std::vector&)")
    qassert(v.p == NULL);
    mem_type = mem_type_;
    is_copy = false;
    *this = vp;
  }
  vector(const vector<M>& vp)
  {
    // TIMER("vector::vector(&)")
#ifndef QLAT_USE_ACC
    qassert(vp.is_copy);
#endif
    is_copy = true;
    qassert(vp.mem_type == MemType::Uvm);
    mem_type = vp.mem_type;
    v = vp.v;
  }
  vector(vector<M>&& vp) noexcept
  {
    // TIMER("vector::vector(&&)")
    is_copy = vp.is_copy;
    mem_type = vp.mem_type;
    v = vp.v;
    vp.is_copy = true;
  }
  //
  ~vector()
  {
    // TIMER("vector::~vector()")
    if (not is_copy) {
      clear();
    }
  }
  //
  void init()
  // does not change mem_type
  {
    if (not is_copy) {
      clear();
    }
    is_copy = false;
  }
  //
  void clear()
  {
    qassert(not is_copy);
    if (v.p != NULL) {
      free_mem(v.p, v.n * sizeof(M), mem_type);
    }
    v = Vector<M>();
    qassert(v.p == NULL);
  }
  //
  void set_mem_type(const MemType mem_type_)
  {
    qassert(not is_copy);
    if (NULL == v.p) {
      mem_type = mem_type_;
      return;
    }
    if (is_same_mem_type(mem_type, mem_type_)) {
      mem_type = mem_type_;
      return;
    }
    {
      TIMER("vector::set_mem_type");
      vector<M> vec;
      qswap(*this, vec);
      mem_type = mem_type_;
      *this = vec;
      qassert(mem_type == mem_type_);
    }
  }
  //
  void set_view(const Vector<M>& vec)
  // does not change mem_type
  {
    init();
    is_copy = true;
    v = vec;
  }
  void set_view(const vector<M>& vec)
  {
    init();
    is_copy = true;
    mem_type = vec.mem_type;
    v = vec.v;
  }
  //
  template <class N>
  void set_view_cast(const Vector<N>& vec)
  // does not change mem_type
  {
    init();
    is_copy = true;
    v.set_cast(vec.v);
  }
  template <class N>
  void set_view_cast(const vector<N>& vec)
  {
    init();
    is_copy = true;
    mem_type = vec.mem_type;
    v.set_cast(vec.v);
  }
  //
  void resize(const Long size)
  {
    qassert(not is_copy);
    qassert(0 <= size);
    if (v.p == NULL) {
      v.p = (M*)alloc_mem(size * sizeof(M), mem_type);
      v.n = size;
      return;
    }
    if (size == v.n) {
      return;
    }
    if (size == 0) {
      clear();
      return;
    }
    {
      TIMER("vector::resize");
      vector<M> vp(size, mem_type);
      qswap(*this, vp);
      const Long n_min = std::min(size, vp.v.n);
      copy_mem(v.p, mem_type, vp.v.p, vp.mem_type, n_min * sizeof(M));
    }
  }
  //
  vector<M>& operator=(const vector<M>& vp)
  // does not change mem_type
  {
    // TIMER("vector::operator=(&)");
    qassert(not is_copy);
    clear();
    resize(vp.size());
    copy_mem(v.p, mem_type, vp.v.p, vp.mem_type, v.n * sizeof(M));
    return *this;
  }
  vector<M>& operator=(vector<M>&& vp) noexcept
  {
    // TIMER("vector::operator=(&&)");
    is_copy = vp.is_copy;
    mem_type = vp.mem_type;
    v = vp.v;
    vp.is_copy = true;
    return *this;
  }
  vector<M>& operator=(const std::vector<M>& vp)
  {
    // TIMER("vector::operator=(std::vector&)");
    qassert(not is_copy);
    clear();
    resize(vp.size());
    copy_mem(v.p, mem_type, vp.data(), MemType::Cpu, v.n * sizeof(M));
    return *this;
  }
  //
  qacc const M& operator[](const Long i) const { return v[i]; }
  qacc M& operator[](const Long i) { return v[i]; }
  //
  qacc Long size() const { return v.size(); }
  //
  qacc M* data() { return v.data(); }
  qacc const M* data() const { return v.data(); }
};

template <class M>
void clear(vector<M>& v)
{
  v.clear();
}

template <class M>
qacc void qswap(vector<M>& v1, vector<M>& v2)
{
  qassert(not v1.is_copy);
  qassert(not v2.is_copy);
  std::swap(v1.mem_type, v2.mem_type);
  std::swap(v1.v, v2.v);
}

template <class M, class N>
qacc void qswap_cast(vector<M>& v1, vector<N>& v2)
{
  qassert(not v1.is_copy);
  qassert(not v2.is_copy);
  std::swap(v1.mem_type, v2.mem_type);
  const Long data_size1 = v2.v.data_size();
  const Long data_size2 = v1.v.data_size();
  const Long size1 = data_size1 / sizeof(M);
  const Long size2 = data_size2 / sizeof(N);
  qassert(size1 * (Long)sizeof(M) == data_size1);
  qassert(size2 * (Long)sizeof(N) == data_size2);
  void* p_tmp = (void*)v1.v.p;
  v1.v.p = (M*)v2.v.p;
  v2.v.p = (N*)p_tmp;
  v1.v.n = size1;
  v2.v.n = size2;
}

// --------------------

template <class M>
qacc bool operator==(const vector<M>& v1, const vector<M>& v2)
{
  if (v1.size() != v2.size()) {
    return false;
  }
  const int cmp = std::memcmp(v1.data(), v2.data(), v1.size() * sizeof(M));
  return cmp == 0;
}

template <class M>
qacc bool operator!=(const vector<M>& v1, const vector<M>& v2)
{
  return not(v1 == v2);
}

// --------------------

template <class M>
struct IsDataVectorType<vector<M>> {
  using DataType = M;
  using BasicDataType = typename IsDataValueType<DataType>::BasicDataType;
  using ElementaryType = typename IsDataValueType<DataType>::ElementaryType;
  static constexpr bool value = is_data_value_type<DataType>();
};

template <class M>
qacc Vector<M> get_data(const vector<M>& v)
{
  return v.v;
}

// --------------------

template <class M>
struct API box {
  //
  // like a one element vector
  //
  // Avoid copy constructor when possible
  // (it is likely not what you think it is)
  // Only used in qacc macros, or if it is already a copy.
  //
  bool is_copy;  // do not free memory if is_copy=true
  MemType mem_type;  // if place data on accelerator memory
  Handle<M> v;
  //
  box()
  {
    // TIMER("box::box()");
    qassert(v.p == NULL);
    is_copy = false;
    mem_type = get_default_mem_type();
  }
  box(const box<M>& vp)
  {
    // TIMER("box::box(&)");
#ifndef QLAT_USE_ACC
    qassert(vp.is_copy);
#endif
    is_copy = true;
    qassert(vp.mem_type == MemType::Uvm);
    mem_type = vp.mem_type;
    v = vp.v;
  }
  box(box<M>&& vp) noexcept
  {
    // TIMER("box::box(&&)");
    is_copy = vp.is_copy;
    mem_type = vp.mem_type;
    v = vp.v;
    vp.is_copy = true;
  }
  box(const M& x, MemType mem_type_ = get_default_mem_type())
  {
    // TIMER("box::box(x)");
    qassert(v.p == NULL);
    is_copy = false;
    mem_type = mem_type_;
    set(x);
  }
  //
  ~box()
  {
    // TIMER("box::~box()");
    if (not is_copy) {
      clear();
    }
  }
  //
  void init()
  // does not change mem_type
  {
    if (not is_copy) {
      clear();
    }
    is_copy = false;
  }
  //
  void clear()
  {
    qassert(not is_copy);
    if (v.p != NULL) {
      free_mem(v.p, sizeof(M), mem_type);
    }
    v = Handle<M>();
    qassert(v.p == NULL);
  }
  //
  void set_mem_type(const MemType mem_type_)
  {
    qassert(not is_copy);
    if (NULL == v.p) {
      mem_type = mem_type_;
      return;
    }
    if (is_same_mem_type(mem_type, mem_type_)) {
      mem_type = mem_type_;
      return;
    }
    {
      TIMER("box::set_mem_type");
      box<M> b;
      qswap(*this, b);
      mem_type = mem_type_;
      *this = b;
      qassert(mem_type == mem_type_);
    }
  }
  //
  void set_view(const M& x)
  // does not change mem_type
  {
    qassert(mem_type != MemType::Acc);
    init();
    is_copy = true;
    v.p = &x;
  }
  void set_view(const Handle<M> h)
  // does not change mem_type
  {
    init();
    is_copy = true;
    v = h;
  }
  void set_view(const box<M>& b)
  {
    init();
    is_copy = true;
    mem_type = b.mem_type;
    v = b.v;
  }
  //
  void alloc()
  {
    qassert(not is_copy);
    if (v.p == NULL) {
      v.p = (M*)alloc_mem(sizeof(M), mem_type);
    }
  }
  //
  void set(const M& x)
  {
    if (mem_type == MemType::Acc) {
      clear();
      mem_type = MemType::Cpu;
      alloc();
      v() = x;
      set_mem_type(MemType::Acc);
      return;
    }
    alloc();
    v() = x;
  }
  //
  box<M>& operator=(const box<M>& vp)
  {
    // TIMER("box::operator=(&)");
    qassert(not is_copy);
    alloc();
    copy_mem(v.p, mem_type, vp.v.p, vp.mem_type, sizeof(M));
    return *this;
  }
  box<M>& operator=(box<M>&& vp) noexcept
  {
    // TIMER("box::operator=(&&)");
    is_copy = vp.is_copy;
    mem_type = vp.mem_type;
    v = vp.v;
    vp.is_copy = true;
    return *this;
  }
  //
  qacc const M& operator()() const { return v(); }
  qacc M& operator()() { return v(); }
  //
  qacc bool null() const { return v.null(); }
};

template <class M>
void clear(box<M>& v)
{
  v.clear();
}

template <class M>
qacc void qswap(box<M>& v1, box<M>& v2)
{
  qassert(not v1.is_copy);
  qassert(not v2.is_copy);
  std::swap(v1.mem_type, v2.mem_type);
  std::swap(v1.v, v2.v);
}

// --------------------

template <class M>
struct IsDataVectorType<box<M>> {
  using DataType = M;
  using BasicDataType = typename IsDataValueType<DataType>::BasicDataType;
  using ElementaryType = typename IsDataValueType<DataType>::ElementaryType;
  static constexpr bool value = is_data_value_type<DataType>();
};

template <class M>
qacc Vector<M> get_data(const box<M>& v)
{
  if (not v.null()) {
    return get_data(v());
  } else {
    return Vector<M>();
  }
}

}  // namespace qlat

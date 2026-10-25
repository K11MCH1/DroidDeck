#include <cassert>
#include "shm_texture_pool.hpp"

struct Texture : gamescope::RcObject
{
    Texture(uint32_t width, uint32_t height, uint32_t format) : w(width), h(height), f(format) { ++alive; }
    ~Texture() override { --alive; }
    uint32_t width() { return w; }
    uint32_t height() { return h; }
    uint32_t drmFormat() { return f; }
    uint64_t totalSize() { return uint64_t(w) * h * 4; }
    bool IsInUse() { return GetRefCount() != 0; }
    uint32_t w, h, f;
    int content = 0;
    static inline int alive = 0;
};

int main()
{
    {
        CShmTexturePool<Texture> pool(128);
        gamescope::OwningRc<Texture> first = new Texture(4, 4, 1);
        first->content = 11;
        pool.retain(first);
        gamescope::Rc<Texture> commit = first;
        gamescope::Rc<Texture> gpu = commit;
        first = nullptr;
        assert(!pool.acquire(4, 4, 1));
        commit = nullptr;
        assert(!pool.acquire(4, 4, 1));
        gpu = nullptr;
        first = pool.acquire(4, 4, 1);
        assert(first && first->content == 11);
        assert(!pool.acquire(4, 4, 1));
        commit = first;
        first = nullptr;
        gamescope::OwningRc<Texture> second = new Texture(4, 4, 1);
        pool.retain(second);
        second->content = 22;
        assert(commit->content == 11);
        assert(!pool.acquire(4, 4, 1));
        second = nullptr;
        second = pool.acquire(4, 4, 1);
        assert(second && second->content == 22);
        assert(!pool.acquire(4, 4, 2));
        assert(!pool.acquire(2, 8, 1));
        gamescope::OwningRc<Texture> oversized = new Texture(16, 16, 1);
        pool.retain(oversized);
        assert(pool.retainedBytes() == 128);
        gamescope::OwningRc<Texture> third = new Texture(4, 4, 2);
        pool.retain(third);
        assert(pool.retainedBytes() == 128);
        assert(!pool.acquire(4, 4, 2));
        second = nullptr;
        pool.retain(third);
        third = nullptr;
        assert(pool.acquire(4, 4, 2));
        assert(pool.retainedBytes() == 128);
        assert(commit->content == 11);
    }
    assert(Texture::alive == 0);
}

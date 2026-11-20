/* DSR sampler requests must reach Metal and remain distinct in the sampler cache.
 * clang -fobjc-arc -framework Metal -framework QuartzCore -framework Foundation -I src/renderer \
 *   recomp/tests/sampler_test.m src/renderer/renderer.m -o /tmp/sampler_test
 * (cd src/renderer && /tmp/sampler_test)
 */
#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#include <assert.h>
#include "renderer.h"
#include "../../src/dsr/dsr_proto.h"

@interface SamplerDevice : NSProxy
@property(nonatomic, strong) id<MTLDevice> realDevice;
@property(nonatomic, strong) NSMutableArray<NSNumber *> *anisotropy;
@end
@implementation SamplerDevice
- (NSMethodSignature *)methodSignatureForSelector:(SEL)s { return [(id)self.realDevice methodSignatureForSelector:s]; }
- (void)forwardInvocation:(NSInvocation *)i { [i invokeWithTarget:self.realDevice]; }
- (id<MTLSamplerState>)newSamplerStateWithDescriptor:(MTLSamplerDescriptor *)d
{
    [self.anisotropy addObject:@(d.maxAnisotropy)];
    return [self.realDevice newSamplerStateWithDescriptor:d];
}
@end
static DSRRenderer *r;
static void cmd(uint32_t op, const void *p, uint32_t n) { dsr_renderer_exec(r, op, p, n); }
static void stage(uint32_t k, uint32_t v) { uint32_t p[]={0,k,v}; cmd(DSR_TSS,p,sizeof p); }
static void draw(void)
{
    struct { uint32_t head[4]; struct { float p[3]; uint32_t color; float uv[2]; } v[3]; } p={.head={4,0x142,3,0},
        .v={{{-1,-1,.5},0xffffffff,{0,0}},{{3,-1,.5},0xffffffff,{2,0}},{{-1,3,.5},0xffffffff,{0,2}}}};
    cmd(DSR_DRAW,&p,sizeof p); dsr_renderer_flush(r,1);
}
int main(void)
{
    @autoreleasepool {
        SamplerDevice *dev=[SamplerDevice alloc]; dev.realDevice=MTLCreateSystemDefaultDevice(); assert(dev.realDevice);
        dev.anisotropy=[NSMutableArray new]; setenv("DSR_RINGMB","4",1);
        r=dsr_renderer_create((id<MTLDevice>)dev); assert(r);
        uint32_t s[]={1,16,16,1,0,0,0,1}; cmd(DSR_SURFACE_CREATE,s,sizeof s);
        uint32_t rt[]={1,0}; cmd(DSR_SET_RT,rt,sizeof rt);
        uint32_t vp[]={0,0,16,16,0,0x3f800000}; cmd(DSR_VIEWPORT,vp,sizeof vp);
        uint32_t z[]={7,0}; cmd(DSR_RENDER_STATE,z,sizeof z);
        uint32_t cull[]={22,1}; cmd(DSR_RENDER_STATE,cull,sizeof cull);
        stage(18,3); stage(17,3); stage(21,8); draw();
        assert([dev.anisotropy containsObject:@8]);
        NSUInteger n=dev.anisotropy.count; draw(); assert(dev.anisotropy.count==n);
        stage(21,16); draw(); assert([dev.anisotropy.lastObject isEqual:@16]);
        stage(21,99); draw(); assert(dev.anisotropy.count==n+1); // clamped request reuses 16x
        stage(21,0); draw(); assert([dev.anisotropy.lastObject isEqual:@1]);
        stage(21,8); draw(); assert(dev.anisotropy.count==n+2); // reuses earlier 8x
        stage(17,2); draw(); assert([dev.anisotropy.lastObject isEqual:@1]); // ordinary linear
        n=dev.anisotropy.count; stage(21,16); draw(); assert(dev.anisotropy.count==n);
        puts("Metal samplers: anisotropy, bounds, ordinary filtering and cache transitions passed");
    }
    return 0;
}

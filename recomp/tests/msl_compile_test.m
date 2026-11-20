/* Compile unique generated MSL sources on the real Metal device. Sources stay local.
 * clang -fobjc-arc -framework Metal -framework Foundation recomp/tests/msl_compile_test.m -o /tmp/msl_compile_test
 * /tmp/msl_compile_test <directory from tools/sdp2msl.c>
 */
#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
int main(int argc, char **argv)
{
    @autoreleasepool {
        if(argc!=2) return 2;
        id<MTLDevice> dev=MTLCreateSystemDefaultDevice(); if(!dev) return 77;
        NSMutableSet<NSString *> *seen=[NSMutableSet new]; unsigned total=0,bad=0;
        for(NSString *file in [NSFileManager.defaultManager contentsOfDirectoryAtPath:@(argv[1]) error:nil]) {
            if(![file.pathExtension isEqual:@"metal"]) continue;
            @autoreleasepool {
                NSString *path=[@(argv[1]) stringByAppendingPathComponent:file];
                NSString *src=[NSString stringWithContentsOfFile:path encoding:NSUTF8StringEncoding error:nil];
                if(!src) { fprintf(stderr,"Unreadable: %s\n",path.UTF8String); bad++; continue; }
                total++; if([seen containsObject:src]) continue; [seen addObject:src];
                NSError *err=nil;
                if(![dev newLibraryWithSource:src options:nil error:&err]) {
                    bad++; fprintf(stderr,"%s: %s\n",file.UTF8String,err.localizedDescription.UTF8String);
                }
            }
        }
        printf("%u source files, %lu unique Metal shaders, %u failed\n",total,(unsigned long)seen.count,bad);
        return bad || total==0 ? 1 : 0;
    }
}

#include <algorithm>
#include <cstdint>
#include <iostream>
#include <limits>
#include <vector>
#include <string>
int min_degree(std::vector<std::vector<uint64_t>> g) {
    const int n=g.size(), words=(n+63)/64;
    if(!n) return 0;
    std::vector<std::vector<uint64_t>> buckets(n,std::vector<uint64_t>(words));
    std::vector<int> degree(n), counts(n);
    for(int v=0;v<n;++v) {
        for(auto word:g[v]) degree[v]+=__builtin_popcountll(word);
        buckets[degree[v]][v/64]|=1ULL<<(v%64); ++counts[degree[v]];
    }
    int minimum=0, width=0;
    for(int remaining=n;remaining;--remaining) {
        if(remaining-1<=width) break;
        while(!counts[minimum]) ++minimum;
        int word=0; while(!buckets[minimum][word]) ++word;
        int v=64*word+__builtin_ctzll(buckets[minimum][word]);
        buckets[minimum][word]&=~(1ULL<<(v%64)); --counts[minimum];
        width=std::max(width,degree[v]);
        auto ns=g[v];
        for(int w=0;w<words;++w) for(uint64_t bits=ns[w];bits;bits&=bits-1) {
            int u=w*64+__builtin_ctzll(bits), old=degree[u], added=0;
            buckets[old][u/64]&=~(1ULL<<(u%64)); --counts[old];
            for(int k=0;k<words;++k) {
                added+=__builtin_popcountll(ns[k]&~g[u][k]);
                g[u][k]|=ns[k];
            }
            g[u][u/64]&=~(1ULL<<(u%64));
            g[u][v/64]&=~(1ULL<<(v%64));
            // added includes u itself; deleting v removes another edge.
            degree[u]=old+added-2;
            buckets[degree[u]][u/64]|=1ULL<<(u%64); ++counts[degree[u]];
            minimum=std::min(minimum,degree[u]);
        }
    }
    return width;
}
// Exact greedy min-fill scores with deterministic vertex-id tie breaking.
int main(int argc, char** argv) {
    int n, m;
    while (std::cin >> n >> m) {
        int words = (n + 63) / 64;
        std::vector<std::vector<uint64_t>> g(n, std::vector<uint64_t>(words));
        for (int i=0,a,b; i<m; ++i) {
            std::cin >> a >> b;
            if(a==b) continue;
            g[a][b/64] |= 1ULL<<(b%64); g[b][a/64] |= 1ULL<<(a%64);
        }
        if(argc>1 && std::string(argv[1])=="degree") {
            std::cout<<min_degree(std::move(g))<<std::endl; continue;
        }
        std::vector<int> degree(n), fill(n), alive(n,1), dirty(n,1);
        bool sampled=argc>1 && std::string(argv[1])=="sampled";
        int width=0;
        for(int remaining=n; remaining; --remaining) {
            // No remaining elimination can exceed the width already observed.
            if(remaining-1<=width) break;
            int best=-1;
            std::vector<int> candidates;
            for(int v=0;v<n;++v) if(alive[v]) {
                candidates.push_back(v);
                if(sampled) {
                    degree[v]=0;
                    for(auto word:g[v]) degree[v]+=__builtin_popcountll(word);
                }
            }
            if(sampled) {
                std::sort(candidates.begin(),candidates.end(),[&](int a,int b) {
                    return degree[a]!=degree[b] ? degree[a]<degree[b] : a<b;
                });
                if(candidates.size()>64) candidates.resize(64);
            }
            for(int v:candidates) {
                if(dirty[v]) {
                    std::vector<int> ns;
                    for(int w=0;w<words;++w) for(uint64_t bits=g[v][w];bits;bits&=bits-1)
                        ns.push_back(w*64+__builtin_ctzll(bits));
                    degree[v]=ns.size(); int twice=0;
                    for(int u:ns) for(int w=0;w<words;++w)
                        twice+=__builtin_popcountll(g[v][w]&~g[u][w]);
                    fill[v]=(twice-degree[v])/2; dirty[v]=0;
                }
                if(best<0 || fill[v]<fill[best] || (fill[v]==fill[best] &&
                    (degree[v]<degree[best] || (degree[v]==degree[best] && v<best)))) best=v;
            }
            auto nsbits=g[best]; std::vector<int> ns;
            for(int w=0;w<words;++w) for(uint64_t bits=nsbits[w];bits;bits&=bits-1)
                ns.push_back(w*64+__builtin_ctzll(bits));
            width=std::max(width,(int)ns.size()); alive[best]=0;
            // All changed scores lie at distance <=2 from the eliminated vertex.
            for(int u:ns) {
                dirty[u]=1;
                for(int w=0;w<words;++w) for(uint64_t bits=g[u][w];bits;bits&=bits-1)
                    dirty[w*64+__builtin_ctzll(bits)]=1;
            }
            for(int u:ns) {
                for(int w=0;w<words;++w) g[u][w]|=nsbits[w];
                g[u][u/64]&=~(1ULL<<(u%64));
                g[u][best/64]&=~(1ULL<<(best%64));
            }
        }
        std::cout<<width<<std::endl;
    }
}

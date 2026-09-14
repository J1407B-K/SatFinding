// Evaluation-only permutation optimization over an already checked proof DAG.
// No claim of global optimality unless the score reaches its trivial upper bound.
#include <algorithm>
#include <chrono>
#include <cmath>
#include <fstream>
#include <iostream>
#include <numeric>
#include <random>
#include <set>
#include <vector>
using namespace std;
struct Result { long long score; int leaves; vector<int> permutation; };
int main(int argc, char **argv) {
    if (argc != 4) return 2;
    ifstream input(argv[1]);
    int n, leaves, steps, edges;
    input >> n >> leaves >> steps >> edges;
    vector<pair<int,int>> required(leaves), parents(steps);
    for (auto &p:required) input >> p.first >> p.second;
    for (auto &p:parents) input >> p.first >> p.second;
    vector<unsigned char> adjacent(n*n), ready(leaves+steps);
    for (int i=0,u,v;i<edges;i++) { input >> u >> v; adjacent[u*n+v]=adjacent[v*n+u]=1; }
    if (!input) return 3;
    auto evaluate = [&](const vector<int>& permutation) {
        long long score=0; int matched=0;
        for (int i=0;i<leaves;i++) {
            auto e=required[i];
            ready[i]=e.first<0 || adjacent[permutation[e.first]*n+permutation[e.second]];
            matched+=ready[i];
        }
        for(int j=0;j<steps;j++) {
            ready[leaves+j]=ready[parents[j].first] && ready[parents[j].second];
            score+=ready[leaves+j];
        }
        return pair<long long,int>(score,matched);
    };
    mt19937_64 rng(730001);
    vector<Result> best;
    set<vector<int>> retained;
    long long evaluations=0;
    auto retain = [&](const vector<int>& p, pair<long long,int> s) {
        if (retained.count(p)) return;
        if (best.size()==12 && make_pair(best.back().score,best.back().leaves)>=s) return;
        best.push_back({s.first,s.second,p}); retained.insert(p);
        sort(best.begin(),best.end(),[](const Result&a,const Result&b){return make_pair(a.score,a.leaves)>make_pair(b.score,b.leaves);});
        if (best.size()>12) {retained.erase(best.back().permutation);best.pop_back();}
    };
    auto start=chrono::steady_clock::now();
    double seconds=atof(argv[2]);
    int restart=0;
    do {
        vector<int> p(n); iota(p.begin(),p.end(),0);
        if(restart++) shuffle(p.begin(),p.end(),rng);
        auto current=evaluate(p); evaluations++; retain(p,current);
        for(int iteration=0;iteration<12000;iteration++) {
            if(chrono::duration<double>(chrono::steady_clock::now()-start).count()>seconds) break;
            int a=rng()%n,b=rng()%n; if(a==b)continue;
            swap(p[a],p[b]); auto candidate=evaluate(p);evaluations++;
            retain(p,candidate);
            // Score dominates; leaf matches break ties and provide a weak gradient.
            double delta=(candidate.first-current.first)+(candidate.second-current.second)/(double)(leaves+1);
            double temperature=5.0*pow(0.005,iteration/12000.0);
            double uniform=(rng()+0.5)/((long double)numeric_limits<uint64_t>::max()+1.0);
            if(delta>=0 || uniform<exp(delta/temperature)) current=candidate;
            else swap(p[a],p[b]);
        }
    } while(chrono::duration<double>(chrono::steady_clock::now()-start).count()<seconds);
    ofstream out(argv[3]);
    out << "{\"evaluations\":" << evaluations << ",\"restarts\":" << restart
        << ",\"seconds\":" << chrono::duration<double>(chrono::steady_clock::now()-start).count()
        << ",\"score_upper_bound\":" << steps << ",\"global_optimality_proven\":"
        << (best.front().score==steps?"true":"false") << ",\"candidates\":[";
    for(size_t i=0;i<best.size();i++) {
        if(i)out<<",";
        out<<"{\"direct_inferences\":"<<best[i].score<<",\"present_leaves\":"<<best[i].leaves<<",\"permutation\":[";
        for(int j=0;j<n;j++){if(j)out<<",";out<<best[i].permutation[j];}
        out<<"]}";
    }
    out<<"]}\n";
}

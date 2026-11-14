// Exact finite-set symmetric exchange checker. No solver code is linked.
#include <algorithm>
#include <array>
#include <cstdint>
#include <iostream>
#include <map>
#include <set>
#include <unordered_set>
#include <vector>
using namespace std;
using V = vector<int>;
using Key = uint64_t;
int n, dim;
Key encode(const V& x) {
    Key k=0; for(int i=0;i<dim;i++) k |= Key(x[i]+8) << (4*i); return k;
}
struct Check { uint64_t pairs=0; bool fail=false; V x,y; int i=-1; int components=0; };
Check check(const set<V>& points) {
    Check r; vector<V> s(points.begin(),points.end());
    unordered_set<Key> keys; for(auto& x:s) keys.insert(encode(x));
    vector<array<unsigned,10>> minus(s.size()), plus(s.size());
    vector<vector<int>> adj(s.size());
    map<Key,int> index; for(int a=0;a<(int)s.size();a++) index[encode(s[a])]=a;
    for(int a=0;a<(int)s.size();a++) for(int i=0;i<dim;i++) for(int j=0;j<dim;j++) if(i!=j) {
        V z=s[a]; z[i]--; z[j]++;
        if (*min_element(z.begin(),z.end()) < -8 || *max_element(z.begin(),z.end()) > 7) continue;
        Key k=encode(z);
        if(keys.count(k)) {minus[a][i] |= 1u<<j; plus[a][j] |= 1u<<i; adj[a].push_back(index[k]);}
    }
    vector<bool> seen(s.size());
    for(int a=0;a<(int)s.size();a++) if(!seen[a]) {
        r.components++; vector<int> todo{a};seen[a]=true;
        while(!todo.empty()) {int b=todo.back();todo.pop_back();for(int c:adj[b]) if(!seen[c]){seen[c]=true;todo.push_back(c);}}
    }
    // Bitsets exhaustively quantify y for each (x,i), without sampling pairs.
    int words=(s.size()+63)/64;
    using Bits=vector<uint64_t>;
    vector<vector<Bits>> less(dim,vector<Bits>(16,Bits(words))), greater=less;
    vector<vector<Bits>> canplus(dim,vector<Bits>(dim,Bits(words)));
    for(int b=0;b<(int)s.size();b++) for(int i=0;i<dim;i++) {
        for(int t=-8;t<=7;t++) {
            if(s[b][i]<t)less[i][t+8][b/64]|=uint64_t(1)<<(b%64);
            if(s[b][i]>t)greater[i][t+8][b/64]|=uint64_t(1)<<(b%64);
        }
        for(int j=0;j<dim;j++)if(plus[b][i]&(1u<<j))canplus[i][j][b/64]|=uint64_t(1)<<(b%64);
    }
    for(int a=0;a<(int)s.size();a++) {
        int first_b=s.size(),first_i=-1;
        for(int i=0;i<dim;i++) {
            Bits good(words);
            unsigned js=minus[a][i];
            while(js){int j=__builtin_ctz(js);js&=js-1;
                for(int w=0;w<words;w++)good[w]|=canplus[i][j][w]&greater[j][s[a][j]+8][w];
            }
            for(int w=0;w<words;w++) {
                uint64_t bad=less[i][s[a][i]+8][w]&~good[w];
                if(bad){int b=64*w+__builtin_ctzll(bad);if(b<first_b){first_b=b;first_i=i;}break;}
            }
        }
        if(first_i>=0){r.pairs=uint64_t(a)*s.size()+first_b+1;r.fail=true;r.x=s[a];r.y=s[first_b];r.i=first_i;return r;}
    }
    r.pairs=uint64_t(s.size())*s.size();
    return r;
}
void vec(const V& v) {cout<<'[';for(int i=0;i<(int)v.size();i++){if(i)cout<<',';cout<<v[i];}cout<<']';}
void emit(string family, int id, int weight, int parity, const set<V>& s, const V& fixed={}) {
    Check c=check(s);
    cout<<"{\"family\":\""<<family<<"\",\"graph_id\":"<<id<<",\"weight\":"<<weight
        <<",\"parity_mask\":"<<parity<<",\"size\":"<<s.size()<<",\"pairs\":"<<c.pairs
        <<",\"failure\":"<<(c.fail?"true":"false")<<",\"exchange_components\":"<<c.components;
    if(!fixed.empty()){cout<<",\"fixed_g\":";vec(fixed);}
    if(c.fail){cout<<",\"x\":";vec(c.x);cout<<",\"y\":";vec(c.y);cout<<",\"i\":"<<c.i;}
    cout<<"}\n"<<flush;
}
void build(int v, V& x, const V& g, const V& deg, set<V>& s) {
    if(v==n){s.insert(x);return;}
    for(int a=0;a<=deg[v];a++){int b=a+g[v];if(b<0 || b>deg[v])continue;x[v]=-a;x[n+v]=b;build(v+1,x,g,deg,s);}
}
int main() {
    int id,weight,m;
    while(cin>>id>>weight>>n>>m) {
        dim=2*n; vector<pair<int,int>> edges(m); V deg(n);
        for(auto& e:edges){cin>>e.first>>e.second;deg[e.first]++;deg[e.second]++;}
        for(int p=0;p<(1<<n);p++) {
            set<V> balances;
            for(int bits=0;bits<(1<<m);bits++) {
                V d(n),g(n);
                for(int e=0;e<m;e++){auto [u,v]=edges[e];if(bits&(1<<e))swap(u,v);d[u]--;d[v]++;}
                for(int v=0;v<n;v++){int pin=(p>>v)&1,pout=(pin+deg[v])%2;int twice=d[v]-pout+pin;if(twice%2) return 2;g[v]=twice/2;}
                balances.insert(g);
            }
            // Independently lift 0/1 arc flows with FIXED internal sigma.
            set<V> lifted; V sigma(n),ref(n);
            for(auto [u,v]:edges){ref[u]--;ref[v]++;}
            for(int v=0;v<n;v++)sigma[v]=(ref[v]-(((p>>v)&1)+deg[v])%2+((p>>v)&1))/2;
            for(int bits=0;bits<(1<<m);bits++) {V g=sigma;
                for(int e=0;e<m;e++)if(bits&(1<<e)){auto [u,v]=edges[e];g[u]++;g[v]--;}
                lifted.insert(g);
            }
            if(lifted!=balances)return 3;
            set<V> s; V x(dim);
            for(auto& g:balances) build(0,x,g,deg,s);
            emit("Gamma",id,weight,p,s);
            bool even=p==0 && all_of(deg.begin(),deg.end(),[](int d){return d%2==0;});
            if(even){auto prime=s;prime.erase(V(dim));emit("Gamma_prime",id,weight,p,prime);}
            for(auto& g:balances) {set<V> slice;build(0,x,g,deg,slice);emit("fixed_g",id,weight,p,slice,g);
                if(even){slice.erase(V(dim));emit("fixed_g_prime",id,weight,p,slice,g);}}
        }
    }
}

package main

import (
	"crypto/sha1"
	"encoding/binary"
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"sort"
)

// Rendezvous (Highest Random Weight) hashing for routing
func hrw(key string, nodes []string) string {
	if len(nodes) == 0 {
		return ""
	}
	type pair struct {
		n string
		w float64
	}
	scores := make([]pair, 0, len(nodes))
	for _, n := range nodes {
		h := sha1.Sum([]byte(key + "::" + n))
		v := binary.BigEndian.Uint64(h[:8])
		// map to (0,1]
		w := 1.0 - (float64(v) / float64(^uint64(0)))
		scores = append(scores, pair{n, w})
	}
	sort.Slice(scores, func(i, j int) bool { return scores[i].w > scores[j].w })
	return scores[0].n
}

func main() {
	cmd := flag.String("cmd", "route", "route|topk")
	key := flag.String("key", "", "routing key")
	nodesJSON := flag.String("nodes", "[]", "JSON array of node names")
	k := flag.Int("k", 2, "top-k nodes for replication")
	flag.Parse()
	var nodes []string
	if err := json.Unmarshal([]byte(*nodesJSON), &nodes); err != nil {
		fmt.Fprintln(os.Stderr, "invalid -nodes JSON")
		os.Exit(2)
	}
	if *key == "" || len(nodes) == 0 {
		fmt.Fprintln(os.Stderr, "-key and -nodes are required")
		os.Exit(2)
	}
	switch *cmd {
	case "route":
		fmt.Println(hrw(*key, nodes))
	case "topk":
		// naive: perturb key by index to pick top-k distinct
		picked := make(map[string]bool)
		out := make([]string, 0, *k)
		for i := 0; len(out) < *k && i < len(nodes)*2; i++ {
			n := hrw(fmt.Sprintf("%s#%d", *key, i), nodes)
			if !picked[n] {
				picked[n] = true
				out = append(out, n)
			}
		}
		b, _ := json.Marshal(out)
		fmt.Println(string(b))
	default:
		fmt.Fprintln(os.Stderr, "unknown -cmd")
		os.Exit(2)
	}
}

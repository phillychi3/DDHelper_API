package main

import (
	"log"
	"net/http"
	"strings"
)

type securedFileSystem struct {
	fs http.FileSystem
}

func (sfs securedFileSystem) Open(path string) (http.File, error) {
	f, err := sfs.fs.Open(path)
	if err != nil {
		return nil, err
	}

	s, err := f.Stat()
	if s.IsDir() {
		index := strings.TrimSuffix(path, "/") + "/index.html"
		if _, err := sfs.fs.Open(index); err != nil {
			return nil, err
		}
	}

	return f, nil
}

func main() {
	fs := http.FileServer(securedFileSystem{http.Dir("C:/Users/phill/Documents/coed_thing/api/images/static")})
	http.Handle("/sfw/", http.StripPrefix("/sfw/", fs))
	err := http.ListenAndServe(":9090", nil)
	if err != nil {
		log.Fatal("ListenAndServe: ", err)
	}
}

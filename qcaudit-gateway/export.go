// Author: liubin
// Created Time : 五  2/07 140:22:15 2020
//
// File Name: export.go
// Description:

package main

import (
	"context"
	"fmt"
	"net/http"
	"net/url"
	"strings"

	log "github.com/sirupsen/logrus"

	pbQC "git.bdmd.com/server/public-frameworks/proto/protoc-gen-go/iyoudoctor/hosp/qc/v3/qcaudit"
	// pbBI "github.com/datamiller/proto/protoc-gen-go/iyoudoctor/hosp/qc"

	"google.golang.org/grpc"
	"google.golang.org/grpc/metadata"
)

const MetadataHeaderPrefix = "Grpc-Metadata-"

func registerDownloadHandler(ctx context.Context, mux *http.ServeMux, conn *grpc.ClientConn) {
	// Register download bi stats file handler
	client := pbQC.NewQCManagerClient(conn)
	// 下载接口路由
	mux.HandleFunc("/hosp/qc/v3/export/download", func(w http.ResponseWriter, r *http.Request) {
		log.Infof("Access %-6s %s", r.Method, r.URL.String())
		ua := r.Header.Get("User-Agent")

		id := r.URL.Query().Get("id")
		if id == "" {
			log.Errorln("Download: Require id")
			http.Error(w, "Require id", http.StatusBadRequest)
			return
		}
		fileName := id
		requestFileName := r.URL.Query().Get("fileName")
		if requestFileName != "" {
			fileName = requestFileName
		}
		if strings.Contains(ua, "MSIE") || strings.Contains(ua, "Edge") {
			fmt.Println("msIE")
			fileName = url.QueryEscape(fileName)
		}
		var pairs []string
		for key, vals := range r.Header {
			for _, val := range vals {
				if key == "Authorization" {
					pairs = append(pairs, "authorization", val)
					continue
				}

				if strings.HasPrefix(key, MetadataHeaderPrefix) {
					pairs = append(pairs, key[len(MetadataHeaderPrefix):], val)
				}
			}
		}
		ctx = metadata.NewOutgoingContext(ctx, metadata.Pairs(pairs...))
        // 下载接口
		rsp, err := client.DownloadFile(ctx, &pbQC.DownloadFileRequest{Id: id})
		if err != nil {
			log.Errorln("Download: gRPC error:", err)
			http.Error(w, "Internal Error", http.StatusInternalServerError)
			return
		}
		// Write response
		contentDisposition := fmt.Sprintf("attachment; filename=%s", fileName)
		w.Header().Set("Content-Disposition", contentDisposition)
		w.Header().Set("Content-Type", "charset=UTF-8")
		w.Header().Set("Content-Type", "application/force-download")
		w.WriteHeader(http.StatusOK)
		if _, err := w.Write(rsp.File); err != nil {
			log.Errorln("Download: Failed to write response body, error:", err)
		}
		// Done
	})
}

/** Author:
 * Created Time : 2021-05-17 17:41
 *
 * File Name: main.go
 * Description:
 *	The hospqc http1.1 json to gRPC gateway
 */
package main

import (
	"context"
	"flag"
	"fmt"
	"net/http"
	"time"

	log "github.com/sirupsen/logrus"

	pbQC "git.bdmd.com/server/public-frameworks/proto/protoc-gen-go/iyoudoctor/hosp/qc/v3/qcaudit"
	pbSample "git.bdmd.com/server/public-frameworks/proto/protoc-gen-go/iyoudoctor/hosp/qc/v3/sample"
	pbStats "git.bdmd.com/server/public-frameworks/proto/protoc-gen-go/iyoudoctor/hosp/qc/v3/stats"
	pbDoctor "git.bdmd.com/server/public-frameworks/proto/protoc-gen-go/iyoudoctor/hosp/qc/v3/doctor"
	pbItem "git.bdmd.com/server/public-frameworks/proto/protoc-gen-go/iyoudoctor/hosp/qc/v3/qcitems"
	pbCdss "git.bdmd.com/server/public-frameworks/proto/protoc-gen-go/iyoudoctor/hosp/qc/v3/qccdss"
	"github.com/grpc-ecosystem/grpc-gateway/v2/runtime"
	"google.golang.org/grpc"
	"google.golang.org/protobuf/encoding/protojson"
)

func main() {
	var host, apiHost string
	var port, apiPort int

	flag.StringVar(&apiHost, "api-host", "localhost", "Host of api grpc service")
	flag.IntVar(&apiPort, "api-port", 6024, "Port of api grpc service")
	flag.StringVar(&host, "host", "0.0.0.0", "Bind host")
	flag.IntVar(&port, "port", 8024, "Bind port")
	flag.Parse()

	// Create gRPC connection
	var conn *grpc.ClientConn
	apiURI := fmt.Sprintf("%s:%d", apiHost, apiPort)
	for {
		var err error
		conn, err = grpc.Dial(apiURI, grpc.WithInsecure(), grpc.WithBackoffMaxDelay(time.Second), grpc.WithDefaultCallOptions(grpc.MaxCallRecvMsgSize(16*1024*1024)))
		if err != nil {
			log.Errorln("Failed to connect to gRPC server, will retry in 5s. Error:", err)
			time.Sleep(5 * time.Second)
			continue
		}
		// Good
		break
	}

	// Create serve mux
	ctx := context.Background()
	ctx, cancel := context.WithCancel(ctx)
	defer cancel()

	// 使用proto定义的字段名作为返回值
    var options = make([]runtime.ServeMuxOption, 0)
    options = append(options, runtime.WithMarshalerOption(runtime.MIMEWildcard, &runtime.JSONPb{
        MarshalOptions:   protojson.MarshalOptions{
            UseProtoNames:     true,
            EmitUnpopulated:   true,
        },
        UnmarshalOptions: protojson.UnmarshalOptions{DiscardUnknown: true},
    }))
	gatewayMux := runtime.NewServeMux(options...)

	if err := pbQC.RegisterQCManagerHandler(ctx, gatewayMux, conn); err != nil {
		log.Fatalln("Failed to register iyoudoctor.hosp.qc.qcManager service to", apiURI)
	}

	if err := pbSample.RegisterQCSampleHandler(ctx, gatewayMux, conn); err != nil {
		log.Fatalln("Failed to register iyoudoctor.hosp.qc.QCSample service to", apiURI)
	}

	if err := pbStats.RegisterStatsManagerHandler(ctx, gatewayMux, conn); err != nil {
		log.Fatalln("Failed to register iyoudoctor.hosp.qc.QCStats service to", apiURI)
	}

	if err := pbDoctor.RegisterDoctorMatterManagerHandler(ctx, gatewayMux, conn); err != nil {
		log.Fatalln("Failed to register iyoudoctor.hosp.qc.pbDoctor service to", apiURI)
	}

	if err := pbItem.RegisterQCItemsManagerHandler(ctx, gatewayMux, conn); err != nil {
    	log.Fatalln("Failed to register iyoudoctor.hosp.qc.v3.qcitems service to", apiURI)
    }

    if err := pbCdss.RegisterQCCDSSManagerHandler(ctx, gatewayMux, conn); err != nil {
    	log.Fatalln("Failed to register iyoudoctor.hosp.qc.v3.qccdss service to", apiURI)
    }

	mux := http.NewServeMux()
    mux.Handle("/", gatewayMux)

	registerDownloadHandler(ctx, mux, conn)

	// start server
	log.Infof("Start server at %s:%d", host, port)
	if err := http.ListenAndServe(fmt.Sprintf("%s:%d", host, port), mux); err != nil {
		log.Fatalln("Failed to start server, error:", err)
	}
}

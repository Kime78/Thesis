package main

import (
	"context"
	"fmt"

	"github.com/gophercloud/gophercloud/v2/openstack"
	"github.com/gophercloud/gophercloud/v2/openstack/compute/v2/keypairs"
	"github.com/gophercloud/gophercloud/v2/openstack/compute/v2/servers"
	"github.com/gophercloud/gophercloud/v2/openstack/compute/v2/volumeattach"
	"github.com/gophercloud/gophercloud/v2/openstack/config"
	"github.com/gophercloud/gophercloud/v2/openstack/config/clouds"
	"github.com/gophercloud/gophercloud/v2/openstack/networking/v2/extensions/layer3/floatingips"
	"github.com/gophercloud/gophercloud/v2/openstack/networking/v2/ports"
)

func main() {
	fmt.Println("Creating server")
	ctx := context.Background()

	// Fetch coordinates from a `cloud.yaml` in the current directory, or
	// in the well-known config directories (different for each operating
	// system).
	authOptions, endpointOptions, tlsConfig, err := clouds.Parse()
	if err != nil {
		panic(err)
	}

	// Call Keystone to get an authentication token, and use it to
	// construct a ProviderClient. All functions hitting the OpenStack API
	// accept a `context.Context` to enable tracing and cancellation.
	providerClient, err := config.NewProviderClient(ctx, authOptions, config.WithTLSConfig(tlsConfig))
	if err != nil {
		panic(err)
	}

	// Use the ProviderClient and the endpoint options fetched from
	// `clouds.yaml` to build a service client: a compute client in this
	// case. Note that the contructor does not accept a `context.Context`:
	// no further call to the OpenStack API is needed at this stage.
	computeClient, err := openstack.NewComputeV2(providerClient, endpointOptions)
	if err != nil {
		panic(err)
	}

	serverCreateOpts := servers.CreateOpts{
        Name:      "go 10!",
		FlavorRef: "370187fc-091a-431b-a787-2dc515911005",
		ImageRef:  "92b19b2f-05e7-4af8-ba33-3c9ddcecb727",
		Networks: []servers.Network{
			{UUID: "72909eea-a022-4353-8314-9b5b7e501cfe"},
		},
    }

	createOpts := keypairs.CreateOptsExt{
		CreateOptsBuilder: serverCreateOpts,
		KeyName:           "rere",
	}

	server, err := servers.Create(context.TODO(), computeClient, createOpts, servers.SchedulerHintOpts{}).Extract()

	if err != nil {
		panic(err)
	}

	fmt.Printf("Server created: %s (ID: %s)\n", server.Name, server.ID)


	fmt.Println("Waiting for the server to start")
	err = servers.WaitForStatus(ctx, computeClient, server.ID, "ACTIVE")
	if err != nil {
		panic(fmt.Errorf("server did not become ACTIVE: %w", err))
	}
	fmt.Println("Server started successfully")
	networkClient, err := openstack.NewNetworkV2(providerClient, endpointOptions)
	if err != nil {
		panic(err)
	}

	portListOpts := ports.ListOpts{
		DeviceID: server.ID,
	}

	portPages, err := ports.List(networkClient, portListOpts).AllPages(ctx)
	if err != nil {
		panic(fmt.Errorf("failed to list ports for server: %w", err))
	}

	portList, err := ports.ExtractPorts(portPages)
	if err != nil {
		panic(fmt.Errorf("failed to extract ports: %w", err))
	}
	if len(portList) == 0 {
		panic("no ports found for server")
	}
	serverPortID := portList[0].ID

	// Replace this with your external (public) network ID
	publicNetworkID := "5abea629-f544-4811-b374-b45022590f1b"

	// Allocate a floating IP and associate it with the server's port
	fipCreateOpts := floatingips.CreateOpts{
		FloatingNetworkID: publicNetworkID,
		PortID:            serverPortID,
	}

	fip, err := floatingips.Create(ctx, networkClient, fipCreateOpts).Extract()
	if err != nil {
		panic(fmt.Errorf("failed to create and associate floating IP: %w", err))
	}

	fmt.Printf("Floating IP created and associated: %s\n", fip.FloatingIP)

	attachOpts := volumeattach.CreateOpts{
		VolumeID: "ee2f168d-995e-4cbe-8f2f-b5df1c63cb4f",
	}
	
	attachment, err := volumeattach.Create(ctx, computeClient, server.ID, attachOpts).Extract()
	if err != nil {
		panic(fmt.Errorf("failed to attach volume: %w", err))
	}
	
	fmt.Printf("Volume attached: ID=%s, Device=%s\n", attachment.VolumeID, attachment.Device)
	// use the computeClient
}
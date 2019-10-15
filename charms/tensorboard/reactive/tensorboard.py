import yaml
from charmhelpers.core import hookenv
from charms import layer
from charms.reactive import set_flag, clear_flag, when, when_any, when_not


@when('charm.started')
def charm_ready():
    layer.status.active('')


@when_any('layer.docker-resource.oci-image.changed', 'config.changed')
def update_image():
    clear_flag('charm.started')


@when('layer.docker-resource.oci-image.available')
@when_not('charm.started')
def start_charm():
    layer.status.maintenance('configuring container')

    image_info = layer.docker_resource.get_info('oci-image')
    service_name = hookenv.service_name()

    port = hookenv.config('port')

    layer.caas_base.pod_spec_set(
        {
            'service': {
                'annotations': {
                    'getambassador.io/config': yaml.dump_all(
                        [
                            {
                                'apiVersion': 'ambassador/v0',
                                'kind': 'Mapping',
                                'name': 'tensorboard-mapping',
                                'prefix': '/tensorboard/',
                                'rewrite': '/',
                                'service': f'{service_name}:{port}',
                                'timeout_ms': 30000,
                            }
                        ]
                    )
                }
            },
            'containers': [
                {
                    'name': 'tensorboard',
                    'imageDetails': {
                        'imagePath': image_info.registry_path,
                        'username': image_info.username,
                        'password': image_info.password,
                    },
                    'command': [
                        '/usr/local/bin/tensorboard',
                        '--logdir=s3://mlpipeline/pipelines',
                        f'-port={port}',
                    ],
                    'config': {
                        'S3_ENDPOINT': 'minio:9000',
                        'S3_VERIFY_SSL': '0',
                        'S3_USE_HTTPS': '0',
                        'AWS_ACCESS_KEY_ID': 'minio',
                        'AWS_SECRET_ACCESS_KEY': 'minio123',
                    },
                    'ports': [{'name': 'tensorboard', 'containerPort': port}],
                }
            ],
        }
    )

    layer.status.maintenance('creating container')
    set_flag('charm.started')

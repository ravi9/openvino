from copy import deepcopy
from dataclasses import dataclass
from functools import lru_cache
from types import MappingProxyType
from warnings import warn

import os
import torch
import torch.overrides

from torch.fx import GraphModule

from openvino.frontend import FrontEndManager
from openvino.frontend.pytorch.decoder import TorchFXPythonDecoder
from openvino.runtime import Core, Type, PartialShape

from typing import Callable, Optional


import numpy as np
def openvino_compile(gm: GraphModule, *args):
    fe_manager = FrontEndManager()
    fe = fe_manager.load_by_framework('pytorch')

    input_shapes = []
    input_types = []
    for idx, input_data in enumerate(args): #subgraph.example_inputs):
        input_types.append(input_data.type())
        input_shapes.append(input_data.size())

    print("type(gm): ", type(gm))
    decoder = TorchFXPythonDecoder(gm, gm, input_shapes=input_shapes, input_types=input_types)

    print("@@Executing fe.load(decoder)")
    im = fe.load(decoder)
    print("!!Decoder loaded successfully!!")

    print("@@Executing fe.convert(im)")
    om = fe.convert(im)
    print("!!Done with convert step!!")

    dtype_mapping = {
        torch.float64: Type.f64,
        torch.float32: Type.f32,
        torch.float16: Type.f16,
        torch.int64: Type.i64,
        torch.int32: Type.i32,
        torch.uint8: Type.u8,
        torch.int8: Type.i8,
        torch.bool: Type.boolean
    }

    for idx, input_data in enumerate(args): 
        om.inputs[idx].get_node().set_element_type(dtype_mapping[input_data.dtype])
        om.inputs[idx].get_node().set_partial_shape(PartialShape(list(input_data.shape)))
    om.validate_nodes_and_infer_types()

    core = Core()
    
    device = 'CPU'

    if os.getenv("OPENVINO_DEVICE") is not None:
        device = os.getenv("OPENVINO_DEVICE")
        assert device in core.available_devices, "Specified device " + device + " is not in the list of OpenVINO Available Devices"

    compiled = core.compile_model(om, device)
    print("!!Returning compiled model!!")
    return compiled

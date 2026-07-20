# Blendshape Transfer

Transfers shape keys from one mesh to another, even across completely different topology.

## Usage

1. In the 3D View, open the Blendshape panel in the sidebar (press N to open the sidebar).
2. Select the Source object (the object with the blendshapes you want to transfer).
3. Select the Target object (the object that will receive the blendshapes).
4. Click the Transfer Blendshapes button to start the transfer.

## Pre-processing modifiers

To increase the quality of the transfer, you can use pre-processing modifiers. There are two available:

1. Subdivision Surface: smooths out the source mesh so the transfer has more data to work with.
2. Displace: displaces geometry to get it closer to the target object.

Sometimes these will significantly increase transfer quality even with default settings, but be careful when using subdivision with high values on dense meshes, since it is very computationally expensive. It usually doesn't need to go above 1 to 2 levels.

Both modifiers can be previewed using a preview checkbox next to their settings.

## Masking

The transfer uses a mask: everything red will be transferred fully, everything blue won't be transferred at all. You can paint the areas you want or don't want to transfer by clicking the "Draw Transfer Mask" button in the UI.

"""
Run angular tests on material definitions for RW2023.

v1 - 14.8.2023
Start of functions, model files, etc.

v2 - 21.8.2023
Trans + glass assemblies changed to better mimic angular properties.
"""

import subprocess as sp
import os


l_max = 1163000.053 # direct normal luminance through a 1.0 specular transmission Trans material

def write_trans_noglass(name, t_vis, roughness):
    with open('.\%s\material.rad' % name, 'w') as f_w:
        
        # first copy over the light materials, etc.
        with open('material.rad', 'r') as f_r:
            for line in f_r:
                f_w.write(line)
        
        # append the new material
        f_w.write('void trans test_surface\n')
        f_w.write('0\n')
        f_w.write('0\n')
        f_w.write('7 %.8f %.8f %.8f 0 %.5f %.8f 1\n' % (t_vis/0.85, t_vis/0.85, t_vis/0.85, roughness, 0.85))


def write_trans(name, t_vis, roughness, dif):
    with open('.\%s\material.rad' % name, 'w') as f_w:
        
        # first copy over the light materials, etc.
        with open('material.rad', 'r') as f_r:
            for line in f_r:
                f_w.write(line)
        
        # append the new material
        f_w.write('void trans test_surface\n')
        f_w.write('0\n')
        f_w.write('0\n')
        f_w.write('7 %.8f %.8f %.8f 0 %.5f %.8f %.8f\n' % (1, 1, 1, roughness, 1, (1.0-dif)))
        
        # append the proxy glass material
        f_w.write('void glass glass_surface\n')
        f_w.write('0\n')
        f_w.write('0\n')
        f_w.write('3 %.12f %.12f %.12f \n' % (t_vis * 1.09, t_vis * 1.09, t_vis * 1.09))

def write_glass(name, t_vis):
    with open('.\%s\material.rad' % name, 'w') as f_w:
        
        # first copy over the light materials, etc.
        with open('material.rad', 'r') as f_r:
            for line in f_r:
                f_w.write(line)
        
        # append the new material
        f_w.write('void glass test_surface\n')
        f_w.write('0\n')
        f_w.write('0\n')
        f_w.write('3 %.8f %.8f %.8f\n' % (t_vis * 1.09, t_vis * 1.09, t_vis * 1.09))
    

def run_rtrace(name, n_material, passes = 100, rays_per_pass = 64, update_every = 20, rotation = 0, mode = 'trans'):
    os.chdir('.\%s' % name)
    
    # make octree
    cmd = ['oconv', '..\sky.rad', '..\source.rad', '>', '%s.oct' % 'source']
    proc = sp.Popen(cmd, shell = True)
    proc.wait()
    
    if rotation > 0:
        cmd = ['xform', '-rz', '%.2f' % rotation, '..\geom.rad', '>', 'geom_rot.rad']
        proc = sp.Popen(cmd, shell = True)
        proc.wait()
        
        if mode == 'trans':
            cmd = ['xform', '-rz', '%.2f' % rotation, '..\glass.rad', '>', 'glass_rot.rad']
            proc = sp.Popen(cmd, shell = True)
            proc.wait()
        
        cmd = ['oconv', '..\sky.rad', '..\source.rad', 'material.rad', 'geom_rot.rad']
        if mode == 'trans':
            cmd.append('glass_rot.rad')
            
        cmd.extend(['>', '%s.oct' % name])
        
    else:
        cmd = ['oconv', '..\sky.rad', '..\source.rad', 'material.rad', '..\geom.rad']
        if mode == 'trans':
            cmd.append('..\glass.rad')
        
        cmd.extend(['>', '%s.oct' % name])
    
    proc = sp.Popen(cmd, shell = True) # perform oconv
    proc.wait()
    
    
    # duplicate ray sources some number of times & make result list
    results = []
    with open('..\sensors.pts', 'r') as f_r:
        with open('sensors.pts', 'w') as f_w:
            for line in f_r:
                results.append(0.0)
                for n in range(rays_per_pass):
                    f_w.write(line)
    
    
    # run rtrace and parse results
    cmd = ['rtrace', '-h', '-ad', '1', '-ar', '0', '-ab', '7', '-lw', '0.000001', '%s.oct' % name, '<', 'sensors.pts'] # , '>', 'output.txt']
    for n_pass in range(passes):
        proc = sp.Popen(cmd, shell = True, stdout=sp.PIPE, stderr=sp.PIPE)
        out,err = proc.communicate()
        
        #read data from stdout
        lines = out.split(b'\r\n')
        
        # parse data
        for n_sensor in range(len(results)):
            pass_l = 0.0
            for n_ray in range(rays_per_pass):
                rgb_str = lines[n_sensor * rays_per_pass + n_ray].split(b'\t')
                this_l = 0.265 * float(rgb_str[0]) + 0.67 * float(rgb_str[1]) + 0.065 * float(rgb_str[2])
                pass_l += this_l * 179.0 / float(rays_per_pass)
                
            if n_pass == 0:
                results[n_sensor] = pass_l
            elif n_pass > 0:
                scale = 1.0 / (1.0 + n_pass)
                results[n_sensor] = pass_l * scale + (1.0 - scale) * results[n_sensor]
        
        
        if ((n_pass % update_every) == 0) and (n_pass > 0) and True:
            # print status
            print('\n# ====================================')
            print('# pass %i\t/\t%s' % (n_pass, name))
            for n_v, val in enumerate(results):
                print('%0i \t\t %.8f' % (n_v, val/l_max))
        
    os.chdir('..')
    
    results = [r / l_max for r in results]
    
    if n_material == 0:
        with open('%s.csv' % name, 'w') as f_w:
            f_w.write("Name,Angle,\"Angular Transmission\"\n")
    
    with open('%s.csv' % name, 'a') as f_w:
        for n_r, r in enumerate(results):
            f_w.write('%s,%i,%.12f\n' % (name, n_r, r))
        
    return(results)



# Run test case
Tvis = 0.75
Roughness = 0.03
Dif = 0.2 
name = 'trans_T%s_R%s_D%s' % (Tvis, Roughness, Dif)

try:
    os.mkdir(name)
except:
    pass
    
write_trans(name, Tvis, Roughness, Dif)
results = run_rtrace(name, 0, rotation = 0, update_every = 19, passes = 20, mode = 'trans')

    
size(300);

real dx = 2.0;
real dy = 3.3;
real dz = 3.0;

int ni = 2;
int nj = 1;
int nk = 1;

pair iso(triple p)
{
    return (
        p.x - p.y,
        p.z + 0.5*(p.x + p.y)
    );
}

void edge(triple a, triple b)
{
    draw(iso(a)--iso(b), black+linewidth(0.8));
}

// Slices between neighboring grid cells.
real sliceGap = 0.12*dx;
path slice1 = iso((dx,0,0))--iso((dx,dy,0))--iso((dx,dy,dz))--iso((dx,0,dz))--cycle;
path slice2 = iso((dx+sliceGap,0,0))--iso((dx+sliceGap,dy,0))--iso((dx+sliceGap,dy,dz))--iso((dx+sliceGap,0,dz))--cycle;
fill(slice1, rgb(0.95,0.65,0.15)+opacity(0.45));
fill(slice2, rgb(0.95,0.65,0.15)+opacity(0.45));

// i-direction
for (int j=0; j<=nj; ++j)
for (int k=0; k<=nk; ++k)
    edge((0,j*dy,k*dz), (ni*dx,j*dy,k*dz));

// j-direction
for (int i=0; i<=ni; ++i)
for (int k=0; k<=nk; ++k)
    edge((i*dx,0,k*dz), (i*dx,nj*dy,k*dz));

// k-direction
for (int i=0; i<=ni; ++i)
for (int j=0; j<=nj; ++j)
    edge((i*dx,j*dy,0), (i*dx,j*dy,nk*dz));

draw(slice1, black+linewidth(0.8));
draw(slice2, black+linewidth(0.8));

label("$\mathsf{j=j_0}$", iso((dx+sliceGap,0,0)) + (-0.1,-0.1), SE, black+fontsize(16pt));

import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { ModeProvider } from "./context/ModeContext";
import Blotter from "./pages/Blotter";
import CourseMapping from "./pages/CourseMapping";
import CvEdgesLab from "./pages/cv-lab/CvEdgesLab";
import CvFeaturesLab from "./pages/cv-lab/CvFeaturesLab";
import CvFiltersLab from "./pages/cv-lab/CvFiltersLab";
import CvLabHome from "./pages/cv-lab/CvLabHome";
import CvModelBenchmarks from "./pages/cv-lab/CvModelBenchmarks";
import CvObjectDetectionLab from "./pages/cv-lab/CvObjectDetectionLab";
import CvOpticalFlowLab from "./pages/cv-lab/CvOpticalFlowLab";
import CvSegmentationLab from "./pages/cv-lab/CvSegmentationLab";
import CvSiftLab from "./pages/cv-lab/CvSiftLab";
import DemoGuide from "./pages/DemoGuide";
import DepthBufferLab from "./pages/graphics-lab/DepthBufferLab";
import Graphics3DLab from "./pages/graphics-lab/Graphics3DLab";
import GraphicsLabHome from "./pages/graphics-lab/GraphicsLabHome";
import Raster2DLab from "./pages/graphics-lab/Raster2DLab";
import Transform2DLab from "./pages/graphics-lab/Transform2DLab";
import VrArConceptsLab from "./pages/graphics-lab/VrArConceptsLab";
import FxDesk from "./pages/FxDesk";
import LimitationsFutureWork from "./pages/LimitationsFutureWork";
import Market3D from "./pages/Market3D";
import MarketIntelligence from "./pages/MarketIntelligence";
import Methodology from "./pages/Methodology";
import Overview from "./pages/Overview";
import RatesBonds from "./pages/RatesBonds";
import Risk from "./pages/Risk";
import Scenario from "./pages/Scenario";
import YieldCurve from "./pages/YieldCurve";

export default function App() {
  return (
    <ModeProvider>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/fx" element={<FxDesk />} />
            <Route path="/rates" element={<RatesBonds />} />
            <Route path="/yield-curve" element={<YieldCurve />} />
            <Route path="/risk" element={<Risk />} />
            <Route path="/scenario" element={<Scenario />} />
            <Route path="/blotter" element={<Blotter />} />
            <Route path="/vision" element={<MarketIntelligence />} />
            <Route path="/3d" element={<Market3D />} />

            <Route path="/academic/cv" element={<CvLabHome />} />
            <Route path="/academic/cv/filters" element={<CvFiltersLab />} />
            <Route path="/academic/cv/edges" element={<CvEdgesLab />} />
            <Route path="/academic/cv/features" element={<CvFeaturesLab />} />
            <Route path="/academic/cv/sift" element={<CvSiftLab />} />
            <Route path="/academic/cv/segmentation" element={<CvSegmentationLab />} />
            <Route path="/academic/cv/optical-flow" element={<CvOpticalFlowLab />} />
            <Route path="/academic/cv/models" element={<CvModelBenchmarks />} />
            <Route path="/academic/cv/object-detection" element={<CvObjectDetectionLab />} />

            <Route path="/academic/graphics" element={<GraphicsLabHome />} />
            <Route path="/academic/graphics/raster" element={<Raster2DLab />} />
            <Route path="/academic/graphics/transform2d" element={<Transform2DLab />} />
            <Route path="/academic/graphics/3d" element={<Graphics3DLab />} />
            <Route path="/academic/graphics/depth" element={<DepthBufferLab />} />
            <Route path="/academic/graphics/vr-ar" element={<VrArConceptsLab />} />

            <Route path="/academic/course-mapping" element={<CourseMapping />} />
            <Route path="/academic/methodology" element={<Methodology />} />
            <Route path="/academic/limitations" element={<LimitationsFutureWork />} />
            <Route path="/academic/demo-guide" element={<DemoGuide />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </ModeProvider>
  );
}

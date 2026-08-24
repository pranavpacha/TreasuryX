import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import Blotter from "./pages/Blotter";
import CvEdgesLab from "./pages/cv-lab/CvEdgesLab";
import CvFeaturesLab from "./pages/cv-lab/CvFeaturesLab";
import CvFiltersLab from "./pages/cv-lab/CvFiltersLab";
import CvModelBenchmarks from "./pages/cv-lab/CvModelBenchmarks";
import CvObjectDetectionLab from "./pages/cv-lab/CvObjectDetectionLab";
import CvOpticalFlowLab from "./pages/cv-lab/CvOpticalFlowLab";
import CvSegmentationLab from "./pages/cv-lab/CvSegmentationLab";
import FxDesk from "./pages/FxDesk";
import DepthBufferLab from "./pages/graphics-lab/DepthBufferLab";
import Graphics3DLab from "./pages/graphics-lab/Graphics3DLab";
import Raster2DLab from "./pages/graphics-lab/Raster2DLab";
import Transform2DLab from "./pages/graphics-lab/Transform2DLab";
import VrArConceptsLab from "./pages/graphics-lab/VrArConceptsLab";
import CompareMarketScreens from "./pages/intelligence/CompareMarketScreens";
import Market3D from "./pages/Market3D";
import MarketIntelligence from "./pages/MarketIntelligence";
import ComputerGraphicsMethodology from "./pages/methodology/ComputerGraphicsMethodology";
import ComputerVisionMethodology from "./pages/methodology/ComputerVisionMethodology";
import CourseMapping from "./pages/methodology/CourseMapping";
import TechnicalEvidence from "./pages/methodology/TechnicalEvidence";
import TreasuryMethodology from "./pages/methodology/TreasuryMethodology";
import Overview from "./pages/Overview";
import RatesBonds from "./pages/RatesBonds";
import Risk from "./pages/Risk";
import Scenario from "./pages/Scenario";
import YieldCurve from "./pages/YieldCurve";
import DemoGuide from "./pages/DemoGuide";
import LimitationsFutureWork from "./pages/LimitationsFutureWork";

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          {/* WORKSTATION */}
          <Route path="/" element={<Overview />} />
          <Route path="/fx" element={<FxDesk />} />
          <Route path="/rates" element={<RatesBonds />} />
          <Route path="/yield-curve" element={<YieldCurve />} />
          <Route path="/risk" element={<Risk />} />
          <Route path="/scenario" element={<Scenario />} />
          <Route path="/blotter" element={<Blotter />} />

          {/* INTELLIGENCE */}
          <Route path="/intelligence/financial-image" element={<MarketIntelligence />} />
          <Route path="/intelligence/compare-screens" element={<CompareMarketScreens />} />

          {/* VISUALIZATION */}
          <Route path="/visualization/3d-market" element={<Market3D />} />

          {/* METHODOLOGY (documentation) */}
          <Route path="/methodology/treasury" element={<TreasuryMethodology />} />
          <Route path="/methodology/computer-vision" element={<ComputerVisionMethodology />} />
          <Route path="/methodology/computer-graphics" element={<ComputerGraphicsMethodology />} />
          <Route path="/methodology/course-mapping" element={<CourseMapping />} />
          <Route path="/methodology/technical-evidence" element={<TechnicalEvidence />} />
          <Route path="/methodology/limitations" element={<LimitationsFutureWork />} />
          <Route path="/methodology/demo-guide" element={<DemoGuide />} />

          {/* Supplementary technical evidence -- syllabus topics with no natural Treasury
              production use, kept as direct evidence rather than forced into the main workflow */}
          <Route path="/evidence/cv/filters" element={<CvFiltersLab />} />
          <Route path="/evidence/cv/edges" element={<CvEdgesLab />} />
          <Route path="/evidence/cv/features" element={<CvFeaturesLab />} />
          <Route path="/evidence/cv/segmentation" element={<CvSegmentationLab />} />
          <Route path="/evidence/cv/optical-flow" element={<CvOpticalFlowLab />} />
          <Route path="/evidence/cv/models" element={<CvModelBenchmarks />} />
          <Route path="/evidence/cv/object-detection" element={<CvObjectDetectionLab />} />
          <Route path="/evidence/graphics/raster" element={<Raster2DLab />} />
          <Route path="/evidence/graphics/transform2d" element={<Transform2DLab />} />
          <Route path="/evidence/graphics/concepts" element={<Graphics3DLab />} />
          <Route path="/evidence/graphics/depth-buffer" element={<DepthBufferLab />} />
          <Route path="/evidence/graphics/vr-ar" element={<VrArConceptsLab />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
